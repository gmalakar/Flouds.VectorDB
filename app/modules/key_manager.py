# =============================================================================
# File: key_manager.py
# Date: 2026-01-01
# Clean KeyManager implementation
# =============================================================================

import os
import sqlite3
from contextlib import contextmanager
from functools import lru_cache
from typing import Optional, Set, Tuple

from cryptography.fernet import Fernet

from app.app_init import APP_SETTINGS
from app.exceptions import (
    DatabaseConnectionError,
    DatabaseCorruptionError,
    DecryptionError,
)
from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log
from app.utils.path_validator import safe_open

logger = get_logger("key_manager")


class Client:
    def __init__(self, client_id: str, client_secret: str, client_type: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.client_type = client_type


class KeyManager:
    """Manage clients DB and encryption for client secrets.

    Keeps secrets out of logs and ensures admin user exists.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or getattr(
            APP_SETTINGS.security, "clients_db_path", "/app/data/clients.db"
        )
        self.clients: dict[str, Client] = {}
        self._token_cache: Set[str] = set()
        self._admin_cache: Set[str] = set()

        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info("Created database directory: %s", db_dir)

        self._init_database()
        logger.info("Using clients database: %s", sanitize_for_log(self.db_path))

        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self.load_clients()

    @contextmanager
    def _get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except sqlite3.OperationalError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database access error: {e}")
            raise DatabaseConnectionError(f"Cannot access database: {e}")
        except sqlite3.DatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database corruption: {e}")
            raise DatabaseCorruptionError(f"Database corruption detected: {e}")
        finally:
            if conn:
                conn.close()

    def _init_database(self) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clients (
                        client_id TEXT PRIMARY KEY,
                        client_secret TEXT NOT NULL,
                        client_type TEXT NOT NULL DEFAULT 'api_user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_client_type 
                    ON clients(client_type)
                """
                )

                cursor.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS update_client_timestamp 
                    AFTER UPDATE ON clients
                    BEGIN
                        UPDATE clients SET updated_at = CURRENT_TIMESTAMP
                        WHERE client_id = NEW.client_id;
                    END
                """
                )

                logger.info("Database schema initialized successfully")
        except (DatabaseCorruptionError, sqlite3.DatabaseError) as e:
            logger.warning("Database init error: %s", str(e))
            self._recover_database()

    def _recover_database(self) -> None:
        logger.warning("Attempting database recovery...")
        if os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.backup"
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(self.db_path, backup_path)
                logger.info("Backed up corrupted database to %s", backup_path)
            except OSError as e:
                logger.error("Failed to backup corrupted database: %s", str(e))
                try:
                    os.remove(self.db_path)
                    logger.info("Removed corrupted database: %s", self.db_path)
                except OSError as remove_error:
                    logger.error(
                        "Failed to remove corrupted database: %s", str(remove_error)
                    )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clients (
                        client_id TEXT PRIMARY KEY,
                        client_secret TEXT NOT NULL,
                        client_type TEXT NOT NULL DEFAULT 'api_user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_client_type 
                    ON clients(client_type)
                """
                )
                cursor.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS update_client_timestamp 
                    AFTER UPDATE ON clients
                    BEGIN
                        UPDATE clients SET updated_at = CURRENT_TIMESTAMP
                        WHERE client_id = NEW.client_id;
                    END
                """
                )
                logger.info("Database recreated successfully")
        except Exception as e:
            raise DatabaseCorruptionError(f"Cannot recover database: {e}")

    def _get_or_create_encryption_key(self) -> bytes:
        key_env = os.getenv("FLOUDS_ENCRYPTION_KEY")
        if key_env:
            candidate = key_env.encode()
            try:
                # Validation: Fernet accepts urlsafe base64-encoded 32-byte keys as bytes
                Fernet(candidate)
                return candidate
            except Exception as e:
                raise ValueError(
                    "FLOUDS_ENCRYPTION_KEY must be 32 url-safe base64-encoded bytes."
                ) from e

        key_dir = os.path.dirname(os.path.abspath(self.db_path))
        key_file = os.path.join(key_dir, ".encryption_key")

        if os.path.exists(key_file):
            with safe_open(key_file, key_dir, "rb") as f:
                return f.read()

        key = Fernet.generate_key()
        os.makedirs(key_dir, exist_ok=True)
        with safe_open(key_file, key_dir, "wb") as f:
            f.write(key)
        logger.info("Generated new encryption key at %s", sanitize_for_log(key_file))
        return key

    @lru_cache(maxsize=1000)
    def _parse_token(self, token: str) -> Optional[Tuple[str, str]]:
        if "|" in token:
            try:
                client_id, client_secret = token.split("|", 1)
                return client_id, client_secret
            except Exception:
                return None
        if ":" in token:
            try:
                client_id, client_secret = token.split(":", 1)
                return client_id, client_secret
            except Exception:
                return None
        return None

    def authenticate_client(self, token: str) -> Optional[Client]:
        try:
            if token not in self._token_cache:
                logger.debug("Token not found in token cache.")
                return None
            parsed = self._parse_token(token)
            if not parsed:
                logger.debug("Token failed to parse.")
                return None
            client_id, client_secret = parsed
            client = self.clients.get(client_id)
            if client and client.client_secret == client_secret:
                return client
            logger.debug(
                "Client credentials do not match for %s", sanitize_for_log(client_id)
            )
            return None
        except Exception as e:
            logger.error("Authentication error: %s", str(e))
            return None

    def is_admin(self, client_id: str) -> bool:
        return client_id in self._admin_cache

    def get_all_tokens(self) -> Set[str]:
        return set(self._token_cache)

    def add_client(
        self, client_id: str, client_secret: str, client_type: str = "api_user"
    ) -> bool:
        try:
            encrypted_secret = self.fernet.encrypt(client_secret.encode()).decode()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO clients (client_id, client_secret, client_type) VALUES (?, ?, ?)",
                    (client_id, encrypted_secret, client_type),
                )
            self.clients[client_id] = Client(client_id, client_secret, client_type)
            token = f"{client_id}|{client_secret}"
            self._token_cache.add(token)
            if client_type == "admin":
                self._admin_cache.add(client_id)
            self._parse_token.cache_clear()
            logger.info(
                "Added/updated client: %s (%s)",
                sanitize_for_log(client_id),
                sanitize_for_log(client_type),
            )
            return True
        except (DatabaseConnectionError, DatabaseCorruptionError):
            return False
        except Exception as e:
            logger.error(
                "Failed to add client %s: %s", sanitize_for_log(client_id), str(e)
            )
            return False

    def remove_client(self, client_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
                deleted = cursor.rowcount > 0
            if deleted:
                removed_client = self.clients.pop(client_id, None)
                if removed_client:
                    token = f"{client_id}|{removed_client.client_secret}"
                    self._token_cache.discard(token)
                    self._admin_cache.discard(client_id)
                self._parse_token.cache_clear()
                logger.info("Removed client: %s", sanitize_for_log(client_id))
                return True
            return False
        except (DatabaseConnectionError, DatabaseCorruptionError):
            return False
        except Exception as e:
            logger.error(
                "Failed to remove client %s: %s", sanitize_for_log(client_id), str(e)
            )
            return False

    def load_clients(self) -> None:
        try:
            self.clients = {}
            if not os.path.exists(self.db_path):
                logger.info(
                    "Database file %s does not exist, will be created",
                    sanitize_for_log(self.db_path),
                )
                return
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT client_id, client_secret, client_type FROM clients"
                )
                rows = cursor.fetchall()
                if not rows:
                    logger.info(
                        "No clients found in database %s",
                        sanitize_for_log(self.db_path),
                    )
                    return
                for row in rows:
                    try:
                        client_id = row["client_id"]
                        encrypted_secret = row["client_secret"]
                        client_type = row["client_type"]
                        try:
                            client_secret = self.fernet.decrypt(
                                encrypted_secret.encode()
                            ).decode()
                        except Exception as decrypt_error:
                            logger.error(
                                "Failed to decrypt client secret for %s: %s",
                                sanitize_for_log(client_id),
                                str(decrypt_error),
                            )
                            raise DecryptionError(
                                f"Cannot decrypt client credentials: {decrypt_error}"
                            )
                        client = Client(client_id, client_secret, client_type)
                        self.clients[client_id] = client
                        token = f"{client_id}|{client_secret}"
                        self._token_cache.add(token)
                        if client_type == "admin":
                            self._admin_cache.add(client_id)
                    except DecryptionError:
                        logger.error(
                            "Decryption failed for client %s",
                            sanitize_for_log(client_id),
                        )
                        continue
                    except Exception as client_error:
                        logger.error(
                            "Failed to load client %s: %s",
                            sanitize_for_log(client_id),
                            str(client_error),
                        )
                        continue
                logger.info(
                    "Loaded %d clients from %s",
                    len(self.clients),
                    sanitize_for_log(self.db_path),
                )
        except (DatabaseConnectionError, DatabaseCorruptionError) as e:
            logger.error("Database error loading clients: %s", str(e))
            self.clients = {}
            self._token_cache.clear()
            self._admin_cache.clear()
            raise

    def get_client_stats(self) -> dict:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM clients")
                total = cursor.fetchone()["total"]
                cursor.execute(
                    "SELECT client_type, COUNT(*) as count FROM clients GROUP BY client_type"
                )
                by_type = {
                    row["client_type"]: row["count"] for row in cursor.fetchall()
                }
                return {
                    "total_clients": total,
                    "by_type": by_type,
                    "database_size_bytes": (
                        os.path.getsize(self.db_path)
                        if os.path.exists(self.db_path)
                        else 0
                    ),
                }
        except Exception as e:
            logger.error("Failed to get client stats: %s", str(e))
            return {
                "total_clients": len(self.clients),
                "by_type": {},
                "database_size_bytes": 0,
            }

    def close(self) -> None:
        self._token_cache.clear()
        self._admin_cache.clear()
        try:
            self._parse_token.cache_clear()
        except Exception:
            pass

    def _write_admin_files(self, admin_id: str, admin_secret: str) -> None:
        from datetime import datetime

        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        console_file_path = os.path.join(db_dir, "admin_console.txt")
        creds_file = os.path.join(db_dir, "admin_credentials.txt")

        console_contents = [
            "=== ADMIN CREDENTIALS CREATED ===\n",
            f"Admin Client ID: {admin_id}\n",
            f"Admin Secret: {admin_secret}\n",
            f"Admin Token: {admin_id}|{admin_secret}\n",
            "=== SAVE THESE CREDENTIALS ===\n",
        ]
        try:
            with safe_open(
                console_file_path, db_dir, "w", encoding="utf-8"
            ) as console_file:
                console_file.writelines(console_contents)
            logger.warning(
                "Admin credentials saved to %s", sanitize_for_log(console_file_path)
            )
        except Exception as e:
            logger.error(
                "Failed to save admin console to %s: %s",
                sanitize_for_log(console_file_path),
                str(e),
            )

        try:
            with safe_open(creds_file, db_dir, "w", encoding="utf-8") as f:
                f.write("Flouds VectorDB Admin Credentials\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write("\n")
                f.write(f"Client ID: {admin_id}\n")
                f.write(f"Client Secret: {admin_secret}\n")
                f.write("\n")
                f.write("Usage:\n")
                f.write(f"Authorization: Bearer {admin_id}|{admin_secret}\n")
                f.write("\n")
                f.write("Example:\n")
                f.write(
                    f'curl -H "Authorization: Bearer {admin_id}|{admin_secret}" \\\n+'
                )
                f.write("  http://localhost:19680/api/v1/admin/clients\n")
            logger.warning(
                "Admin credentials saved to: %s",
                sanitize_for_log(os.path.abspath(creds_file)),
            )
        except Exception as e:
            logger.error(
                "Failed to save admin credentials to file %s: %s",
                sanitize_for_log(creds_file),
                str(e),
            )

    def ensure_admin_exists(self) -> None:
        admin_exists = any(c.client_type == "admin" for c in self.clients.values())
        if admin_exists:
            return
        import secrets

        admin_id = "admin"
        while True:
            admin_secret = secrets.token_urlsafe(32)
            if ":" not in admin_secret and "|" not in admin_secret:
                break
        if self.add_client(admin_id, admin_secret, "admin"):
            try:
                self._write_admin_files(admin_id, admin_secret)
            except Exception as e:
                logger.error("Failed to create admin credential files: %s", str(e))
        else:
            logger.error("Failed to create admin user")


key_manager = KeyManager()
key_manager.ensure_admin_exists()
