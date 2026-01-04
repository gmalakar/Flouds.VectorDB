# =============================================================================
# File: auth.py
# Date: 2025-01-27
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
import time
from typing import Awaitable, Callable, Dict

from fastapi import Header, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.app_init import APP_SETTINGS
from app.logger import get_logger
from app.models.base_response import BaseResponse
from app.modules.key_manager import key_manager
from app.modules.offender_manager import offender_manager
from app.utils.log_sanitizer import sanitize_for_log
from app.utils.performance_tracker import perf_tracker

logger = get_logger("auth")


def common_headers(
    tenant_code: str = Header(
        "", alias="X-Tenant-Code", description="Tenant code for request"
    ),
) -> Dict[str, str]:
    """Dependency that declares common headers used across endpoints.

    This is used for documentation purposes (OpenAPI) so routes show the
    `X-Tenant-Code` header input box in the UI. Authorization is exposed via
    the global HTTPBearer security scheme (the Authorize button) rather than
    a per-endpoint header input to avoid duplication in the docs.
    """
    return {"tenant_code": tenant_code}


def get_db_token(
    db_token: str = Header(
        ...,  # required
        alias="Flouds-VectorDB-Token",
        description="Database credential token in format user|password or user:password",
        convert_underscores=False,
    )
) -> str:
    """Fetch `Flouds-VectorDB-Token` DB credential header or raise 401 if missing."""
    if not db_token:
        logger.error("Missing Flouds-VectorDB-Token header for DB credentials.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing DB authorization header",
        )
    return db_token


class AuthMiddleware(BaseHTTPMiddleware):
    """API Key authentication middleware for Bearer token validation."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = APP_SETTINGS.security.enabled

        # Cache valid keys count at startup to avoid repeated calls
        # Ensure key_manager has latest clients loaded into memory
        try:
            key_manager.load_clients()
        except Exception:
            logger.exception(
                "Failed to load clients during auth middleware initialization"
            )

        self._keys_configured = (
            bool(key_manager.get_all_tokens()) if self.enabled else True
        )

        # Cache public endpoints for faster lookup
        self.public_endpoints = frozenset(
            [
                "/",
                "/api/v1",
                "/api/v1/metrics",
                "/api/v1/health",
                "/api/v1/health/live",
                "/api/v1/health/ready",
                "/api/v1/docs",
                "/api/v1/redoc",
                "/api/v1/openapi.json",
                "/favicon.ico",
            ]
        )

        # Log security status on startup
        if self.enabled:
            valid_keys = key_manager.get_all_tokens()
            if valid_keys:
                logger.info(
                    f"API authentication enabled with {len(valid_keys)} client(s)"
                )
            else:
                logger.warning("API authentication enabled but no clients configured")
        else:
            logger.info("API authentication disabled")

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with API key authentication."""

        # Determine if authentication checks should be skipped, but still
        # enforce tenant header presence for non-public endpoints.
        skip_auth = not self.enabled

        # Skip auth for public endpoints (optimized lookup)
        path = request.url.path
        # Allow both API-prefixed health endpoints and root-level /health to bypass auth
        if path in self.public_endpoints or path.startswith("/api/v1/health/"):
            return await call_next(request)

        # Require tenant header for all non-public endpoints. However,
        # integrate offender tracking: if the client IP is currently blocked
        # return 429. If header missing, register an offender attempt (tenant
        # 'master') and return 401 unless the register call triggered a block.
        tenant_header = request.headers.get("X-Tenant-Code")

        # Helper to extract client IP
        def _get_client_ip(req: Request) -> str:
            xff = req.headers.get("X-Forwarded-For")
            if xff:
                return xff.split(",", 1)[0].strip()
            client = getattr(req, "client", None)
            try:
                return (
                    client.host
                    if client and getattr(client, "host", None)
                    else "unknown"
                )
            except Exception:
                return "unknown"

        client_ip = _get_client_ip(request)

        # Offender check via shared OffenderManager
        try:
            blocked, blocked_until = offender_manager.is_blocked(client_ip)
        except Exception:
            blocked, blocked_until = False, 0.0

        if blocked:
            reason = f"Requests from {client_ip} temporarily blocked until {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(blocked_until))} UTC"
            error_response = BaseResponse(
                success=False,
                message="Blocked due to repeated unauthenticated requests",
                tenant_code=None,
                time_taken=0.0,
                results=None,
                # include reason in warnings for caller visibility
            )
            return JSONResponse(
                status_code=429,
                content={**error_response.model_dump(), "warnings": [reason]},
            )

        if not tenant_header:
            # register attempt and possibly block; tenant unknown -> use 'master'
            try:
                blocked_now, reason = offender_manager.register_attempt(
                    client_ip, tenant="master"
                )
            except Exception:
                blocked_now, reason = False, ""

            if blocked_now:
                error_response = BaseResponse(
                    success=False,
                    message="Blocked due to repeated unauthenticated requests",
                    tenant_code=None,
                    time_taken=0.0,
                    results=None,
                )
                return JSONResponse(
                    status_code=429,
                    content={**error_response.model_dump(), "warnings": [reason]},
                )

            error_response = BaseResponse(
                success=False,
                message="Missing X-Tenant-Code header",
                tenant_code=None,
                time_taken=0.0,
                results=None,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_response.model_dump(),
            )

        # If authentication is disabled, populate request.state and continue.
        if skip_auth:
            request.state.tenant_code = tenant_header
            return await call_next(request)

        # Check if keys are configured (cached check)
        if not self._keys_configured:
            logger.error("Authentication enabled but no API keys configured")
            error_response = BaseResponse(
                success=False,
                message="Authentication misconfigured",
                tenant_code=None,
                time_taken=0.0,
                results=None,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response.model_dump(),
            )

        # Extract and validate token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = None

        if auth_header and auth_header.startswith("Bearer ") and len(auth_header) > 7:
            token = auth_header[7:].strip()
        elif not APP_SETTINGS.app.is_production:
            # Check for token in query parameter only in development
            token = request.query_params.get("token")

        if not token:
            error_response = BaseResponse(
                success=False,
                message="Missing Authorization header"
                + (" or token parameter" if not APP_SETTINGS.app.is_production else ""),
                tenant_code=None,
                time_taken=0.0,
                results=None,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_response.model_dump(),
            )

        # Use tenant header (required above) when authenticating
        tenant_code = tenant_header or ""
        with perf_tracker.track("auth_client_lookup"):
            client = key_manager.authenticate_client(token, tenant_code=tenant_code)

        if not client:
            # Avoid logging raw tokens or secrets. Log only masked client id.
            try:
                if token and ("|" in token or ":" in token):
                    cid = (
                        token.split("|", 1)[0]
                        if "|" in token
                        else token.split(":", 1)[0]
                    )
                    masked = f"{cid}|***"
                else:
                    masked = "***"
            except Exception:
                masked = "***"
            logger.warning(
                "Authentication failed for API token: %s", sanitize_for_log(masked)
            )
            error_response = BaseResponse(
                success=False,
                message="Invalid API token",
                tenant_code=None,
                time_taken=0.0,
                results=None,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_response.model_dump(),
            )

        # Store client info in request state for downstream use
        request.state.client_id = client.client_id
        request.state.client_type = client.client_type
        # Record tenant for downstream handlers
        request.state.tenant_code = tenant_code or getattr(client, "tenant_code", "")

        logger.debug(
            f"Client authenticated: {sanitize_for_log(client.client_id)} ({client.client_type})"
        )

        return await call_next(request)


# Authenticated client info is available via request.state.client_id and request.state.client_type
