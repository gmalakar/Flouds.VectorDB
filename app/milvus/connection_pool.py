# =============================================================================
# File: connection_pool.py
# Date: 2025-08-01
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import time
from threading import Lock
from typing import Dict, Optional

from pymilvus import MilvusClient

from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log

logger = get_logger("connection_pool")


class MilvusConnectionPool:
    """
    Thread-safe connection pool for MilvusClient instances.

    Manages a pool of Milvus connections, reusing or expiring them based on idle time and pool size.
    Ensures thread safety for concurrent access.

    Attributes:
        max_connections (int): Maximum number of connections in the pool.
        max_idle_time (int): Maximum idle time (seconds) before a connection is expired.
        connections (Dict[str, dict]): Mapping of connection keys to connection info.
        lock (Lock): Thread lock for synchronizing access.
    """

    def __init__(self, max_connections: int = 10, max_idle_time: int = 300) -> None:
        """
        Initialize the connection pool.

        Args:
            max_connections (int, optional): Maximum number of connections. Defaults to 10.
            max_idle_time (int, optional): Maximum idle time in seconds. Defaults to 300.
        """
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.connections: Dict[str, dict] = {}
        self.lock = Lock()

    def get_connection(
        self, uri: str, user: str, password: str, database: Optional[str] = None
    ) -> MilvusClient:
        """
        Get or create a MilvusClient connection from the pool.

        Args:
            uri (str): Milvus server URI.
            user (str): Username for authentication.
            password (str): Password for authentication.
            database (str, optional): Database name. Defaults to None.

        Returns:
            MilvusClient: A connected MilvusClient instance.

        Raises:
            ConnectionError: If connection to Milvus fails.
            ValueError: If connection parameters are invalid.
            RuntimeError: If client is misconfigured or an unexpected error occurs.
        """
        key = f"{user}@{uri}/{database or 'default'}"

        with self.lock:
            # Check if connection exists and is valid
            if key in self.connections:
                conn_info = self.connections[key]
                if time.time() - conn_info["last_used"] < self.max_idle_time:
                    conn_info["last_used"] = time.time()
                    return conn_info["client"]
                else:
                    # Remove expired connection
                    del self.connections[key]

            # Create new connection if under limit
            if len(self.connections) < self.max_connections:
                try:
                    client = MilvusClient(
                        uri=uri,
                        user=user,
                        password=password,
                        db_name=(database or "default"),
                    )
                    self.connections[key] = {
                        "client": client,
                        "last_used": time.time(),
                        "created": time.time(),
                    }
                    logger.debug("Created new Milvus connection: %s", sanitize_for_log(key))
                    return client
                except (ConnectionError, TimeoutError) as e:
                    logger.error("Connection failed to Milvus: %s", e)
                    raise ConnectionError("Failed to connect to Milvus at %s" % uri) from e
                except (ValueError, TypeError) as e:
                    logger.error("Invalid connection parameters: %s", e)
                    raise ValueError("Invalid Milvus connection parameters") from e
                except (ImportError, AttributeError) as e:
                    logger.error("Milvus client configuration error: %s", e)
                    raise RuntimeError("Milvus client misconfigured") from e
                except Exception as e:
                    logger.error("Unexpected error creating Milvus connection: %s", e)
                    raise RuntimeError("Failed to create Milvus connection") from e
            else:
                # Remove oldest connection and create new one
                oldest_key = min(
                    self.connections.keys(),
                    key=lambda k: self.connections[k]["last_used"],
                )
                del self.connections[oldest_key]

                client = MilvusClient(
                    uri=uri,
                    user=user,
                    password=password,
                    db_name=(database or "default"),
                )
                self.connections[key] = {
                    "client": client,
                    "last_used": time.time(),
                    "created": time.time(),
                }
                logger.debug("Replaced oldest connection with: %s", sanitize_for_log(key))
                return client

    def cleanup_expired(self) -> None:
        """
        Remove expired connections from the pool based on idle time.

        This method is thread-safe and can be called periodically to free resources.

        Returns:
            None
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, conn_info in self.connections.items()
                if current_time - conn_info["last_used"] > self.max_idle_time
            ]

            for key in expired_keys:
                del self.connections[key]
                logger.debug("Removed expired connection: %s", sanitize_for_log(key))

    def get_stats(self) -> dict:
        """
        Get statistics about the current state of the connection pool.

        Returns:
            dict: Dictionary with keys:
                - active_connections (int): Number of active connections.
                - max_connections (int): Maximum allowed connections.
                - connections (list[dict]): List of connection details (key, age_seconds, idle_seconds).
        """
        with self.lock:
            return {
                "active_connections": len(self.connections),
                "max_connections": self.max_connections,
                "connections": [
                    {
                        "key": sanitize_for_log(key),
                        "age_seconds": time.time() - info["created"],
                        "idle_seconds": time.time() - info["last_used"],
                    }
                    for key, info in self.connections.items()
                ],
            }

    def close(self) -> None:
        """
        Close all connections in the pool gracefully.

        This method should be called during application shutdown to ensure
        all Milvus connections are properly closed. Thread-safe.

        Returns:
            None
        """
        with self.lock:
            closed_count = 0
            for key, conn_info in list(self.connections.items()):
                try:
                    client = conn_info["client"]
                    if hasattr(client, "close"):
                        client.close()
                    closed_count += 1
                    logger.debug("Closed Milvus connection: %s", sanitize_for_log(key))
                except Exception as e:
                    logger.warning("Error closing connection %s: %s", sanitize_for_log(key), e)
                finally:
                    # Always remove from pool even if close fails
                    if key in self.connections:
                        del self.connections[key]

            if closed_count > 0:
                logger.info("Connection pool closed: %d connections closed", closed_count)
            self.connections.clear()


# Global connection pool instance
milvus_pool = MilvusConnectionPool()
