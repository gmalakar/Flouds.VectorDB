# =============================================================================
# File: cleanup.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from app.logger import get_logger
from app.middleware.tenant_rate_limit import tenant_limiter
from app.milvus.connection_pool import milvus_pool

logger = get_logger("cleanup_task")


async def cleanup_connections() -> None:
    """
    Background async task to periodically clean up expired Milvus connections and inactive tenants.

    This task runs in an infinite loop, calling `milvus_pool.cleanup_expired()` and
    `tenant_limiter.cleanup_inactive_tenants()` every minute. Handles connection, system,
    and module errors gracefully, logging details and continuing. Cancels cleanly on
    asyncio.CancelledError.

    Returns:
        None
    """
    while True:
        try:
            milvus_pool.cleanup_expired()
            removed_tenants = tenant_limiter.cleanup_inactive_tenants(
                max_inactive_seconds=3600
            )
            if removed_tenants > 0:
                logger.debug(f"Rate limiter cleanup: removed {removed_tenants} inactive tenants")
            await asyncio.sleep(60)  # Run every minute
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Connection error during cleanup: {e}")
            await asyncio.sleep(60)
        except (OSError, PermissionError) as e:
            logger.error(f"System error during cleanup: {e}")
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
            break
        except (ImportError, AttributeError) as e:
            logger.error(f"Module error in cleanup task: {e}", exc_info=True)
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(
                f"Unexpected error in connection cleanup task: {e}", exc_info=True
            )
            await asyncio.sleep(60)
