# =============================================================================
# File: admin.py
# Date: 2026-01-01
# =============================================================================
import hashlib
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status

from app.modules.key_manager import key_manager
from app.utils.log_sanitizer import sanitize_for_log

router = APIRouter()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _masked(s: str, n: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= n * 2:
        return s
    return f"{s[:n]}...{s[-n:]}"


@router.get("/fingerprints")
def list_fingerprints(request: Request) -> Dict[str, Any]:
    """Admin-only endpoint that returns masked fingerprints for configured clients.

    Response shape:
      {"clients": [{"client_id": "admin", "fingerprint": "sha256hex", "masked": "adm...min"}, ...]}

    This endpoint never returns raw secrets.
    """
    client_type = getattr(request.state, "client_type", None)
    # Allow both 'admin' and 'superadmin' client types to access admin endpoints
    if client_type not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    results: List[Dict[str, Any]] = []
    for cid, client in key_manager.clients.items():
        try:
            fingerprint = _sha256(client.client_secret)
            results.append(
                {
                    "client_id": sanitize_for_log(cid),
                    "fingerprint": fingerprint,
                    "masked": _masked(client.client_secret),
                }
            )
        except Exception:
            continue

    return {"clients": results}
