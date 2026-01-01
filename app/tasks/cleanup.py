# =============================================================================
# File: cleanup.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import asyncio

from app.logger import get_logger
from app.milvus.connection_pool import milvus_pool

logger = get_logger("cleanup_task")


async def cleanup_connections() -> None:
    """
    Background async task to periodically clean up expired Milvus connections.

    This task runs in an infinite loop, calling `milvus_pool.cleanup_expired()` every minute.
    Handles connection, system, and module errors gracefully, logging details and continuing.
    Cancels cleanly on asyncio.CancelledError.

    Returns:
        None
    """
    while True:
        try:
            milvus_pool.cleanup_expired()
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
