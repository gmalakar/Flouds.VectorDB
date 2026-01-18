# =============================================================================
# File: key_manager.py
# Date: 2026-01-18
# Copyright (c) 2026 Goutam Malakar. All rights reserved.
# =============================================================================

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
from app.exceptions import DatabaseConnectionError, DatabaseCorruptionError, DecryptionError
from app.logger import get_logger
from app.utils.log_sanitizer import sanitize_for_log
from app.utils.path_validator import safe_open

logger = get_logger("key_manager")


# Use a module-level cached function to avoid retaining `self` on instance methods
@lru_cache(maxsize=1000)
def _parse_token_cached(token: str) -> Optional[Tuple[str, str]]:
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


class Client:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        client_type: str,
        tenant_code: str = "",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.client_type = client_type
        self.tenant_code = tenant_code


class KeyManager:
    """Manage clients DB and encryption for client secrets.

    Keeps secrets out of logs and ensures admin user exists.
    """

    def __init__(self, db_path: Optional[str] = None):
        # Ensure we always end up with a str for mypy/os.path calls.
        candidate = (
            db_path
            if db_path is not None
            else getattr(APP_SETTINGS.security, "clients_db_path", "/app/data/clients.db")
        )
        if candidate is None:
            candidate = "/app/data/clients.db"
        self.db_path: str = str(candidate)
        self.clients: dict[str, Client] = {}
        self._token_cache: Set[str] = set()
        self._admin_cache: Set[str] = set()

        db_dir = os.path.dirname(os.path.abspath(str(self.db_path)))
        if db_dir and not os.path.exists(str(db_dir)):
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
                        tenant_code TEXT NOT NULL DEFAULT '',
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

                # Ensure tenant_code column exists for backward compatibility
                try:
                    cursor.execute("PRAGMA table_info(clients)")
                    cols = [r[1] for r in cursor.fetchall()]
                    if "tenant_code" not in cols:
                        cursor.execute("ALTER TABLE clients ADD COLUMN tenant_code TEXT DEFAULT ''")
                except Exception:
                    pass

                logger.info("Database schema initialized successfully")
        except (DatabaseCorruptionError, sqlite3.DatabaseError) as e:
            logger.warning("Database init error: %s", str(e))
            self._recover_database()

    def _recover_database(self) -> None:
        logger.warning("Attempting database recovery...")
        if os.path.exists(str(self.db_path)):
            backup_path = f"{self.db_path}.backup"
            try:
                if os.path.exists(str(backup_path)):
                    os.remove(backup_path)
                os.rename(self.db_path, backup_path)
                logger.info("Backed up corrupted database to %s", backup_path)
            except OSError as e:
                logger.error("Failed to backup corrupted database: %s", str(e))
                try:
                    os.remove(self.db_path)
                    logger.info("Removed corrupted database: %s", self.db_path)
                except OSError as remove_error:
                    logger.error("Failed to remove corrupted database: %s", str(remove_error))

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clients (
                        client_id TEXT PRIMARY KEY,
                        client_secret TEXT NOT NULL,
                        client_type TEXT NOT NULL DEFAULT 'api_user',
                        tenant_code TEXT NOT NULL DEFAULT '',
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

    def _parse_token(self, token: str) -> Optional[Tuple[str, str]]:
        return _parse_token_cached(token)

    def authenticate_client(self, token: str, tenant_code: str = "") -> Optional[Client]:
        try:
            # signature now supports tenant_code matching; caller may pass tenant_code via keyword
            # but to keep backward compatibility, accept tokens without tenant enforcement when tenant_code is empty
            # The method signature was not changed here to preserve callers; the AuthMiddleware will call with tenant_code.
            # For type-checkers, we handle optional tenant by checking function arguments via kwargs when invoked.
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
                # enforce tenant_code match when provided
                if tenant_code and getattr(client, "tenant_code", "") != tenant_code:
                    logger.warning(
                        "Tenant code mismatch for client %s: expected %s",
                        sanitize_for_log(client_id),
                        sanitize_for_log(getattr(client, "tenant_code", "")),
                    )
                    return None
                return client
            logger.debug("Client credentials do not match for %s", sanitize_for_log(client_id))
            return None
        except Exception as e:
            logger.error("Authentication error: %s", str(e))
            return None

    def is_admin(self, client_id: str, tenant_code: str = "") -> bool:
        """Return True if the client is an admin for the given tenant.

        - `superadmin` clients have admin rights across all tenants.
        - `admin` clients have admin rights only for their configured `tenant_code`.
        - If `tenant_code` is empty, `admin` is considered True only when the
          caller does not request tenant scoping (backwards compatible behaviour).
        """
        client = self.clients.get(client_id)
        if not client:
            return False
        if self.is_super_admin(client_id):
            return True
        ctype = getattr(client, "client_type", "")
        if ctype == "admin":
            # If tenant_code is provided, require match. If not provided, preserve
            # backward compatibility by returning True for admin clients.
            if not tenant_code:
                return True
            return getattr(client, "tenant_code", "") == tenant_code
        return False

    def is_super_admin(self, client_id: str) -> bool:
        """Return True if the given client_id is a superadmin."""
        client = self.clients.get(client_id)
        return bool(client and getattr(client, "client_type", "") == "superadmin")

    def any_superadmin_exists(self) -> bool:
        """Return True if any superadmin client exists in the current cache."""
        return any(getattr(c, "client_type", "") == "superadmin" for c in self.clients.values())

    def get_all_tokens(self) -> Set[str]:
        return set(self._token_cache)

    def add_client(
        self,
        client_id: str,
        client_secret: str,
        client_type: str = "api_user",
        tenant_code: str = "",
        created_by: Optional[str] = None,
    ) -> bool:
        """Add client with optional tenant_code support (maintains backward compatibility)."""
        try:
            # Enforce that only a superadmin can create another superadmin once one exists.
            if client_type == "superadmin":
                existing_super = self.any_superadmin_exists()
                if existing_super:
                    if not created_by:
                        logger.warning(
                            "Attempt to create superadmin without superadmin creator: %s",
                            sanitize_for_log(client_id),
                        )
                        return False
                    creator = self.clients.get(created_by)
                    if not creator or creator.client_type != "superadmin":
                        logger.warning(
                            "Creator %s is not authorized to create superadmin",
                            sanitize_for_log(created_by),
                        )
                        return False
            encrypted_secret = self.fernet.encrypt(client_secret.encode()).decode()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO clients (client_id, client_secret, client_type, tenant_code) VALUES (?, ?, ?, ?)",
                    (client_id, encrypted_secret, client_type, tenant_code),
                )
            self.clients[client_id] = Client(
                client_id, client_secret, client_type, tenant_code=tenant_code
            )
            token = f"{client_id}|{client_secret}"
            self._token_cache.add(token)
            if client_type in ("admin", "superadmin"):
                self._admin_cache.add(client_id)
            try:
                _parse_token_cached.cache_clear()
            except Exception:
                pass
            logger.info(
                "Added/updated client: %s (%s)",
                sanitize_for_log(client_id),
                sanitize_for_log(client_type),
            )
            return True
        except (DatabaseConnectionError, DatabaseCorruptionError):
            return False
        except Exception as e:
            logger.error("Failed to add client %s: %s", sanitize_for_log(client_id), str(e))
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
                try:
                    _parse_token_cached.cache_clear()
                except Exception:
                    pass
                logger.info("Removed client: %s", sanitize_for_log(client_id))
                return True
            return False
        except (DatabaseConnectionError, DatabaseCorruptionError):
            return False
        except Exception as e:
            logger.error("Failed to remove client %s: %s", sanitize_for_log(client_id), str(e))
            return False

    def load_clients(self) -> None:
        try:
            self.clients = {}
            if not os.path.exists(str(self.db_path)):
                logger.info(
                    "Database file %s does not exist, will be created",
                    sanitize_for_log(self.db_path),
                )
                return
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT client_id, client_secret, client_type, COALESCE(tenant_code, '') as tenant_code FROM clients"
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
                        tenant_code = row["tenant_code"] if "tenant_code" in row.keys() else ""
                        try:
                            client_secret = self.fernet.decrypt(encrypted_secret.encode()).decode()
                        except Exception as decrypt_error:
                            logger.error(
                                "Failed to decrypt client secret for %s: %s",
                                sanitize_for_log(client_id),
                                str(decrypt_error),
                            )
                            raise DecryptionError(
                                f"Cannot decrypt client credentials: {decrypt_error}"
                            )
                        client = Client(
                            client_id,
                            client_secret,
                            client_type,
                            tenant_code=tenant_code,
                        )
                        self.clients[client_id] = client
                        token = f"{client_id}|{client_secret}"
                        self._token_cache.add(token)
                        if client_type in ("admin", "superadmin"):
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
                by_type = {row["client_type"]: row["count"] for row in cursor.fetchall()}
                return {
                    "total_clients": total,
                    "by_type": by_type,
                    "database_size_bytes": (
                        os.path.getsize(str(self.db_path))
                        if os.path.exists(str(self.db_path))
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
            _parse_token_cached.cache_clear()
        except Exception:
            pass

    def _write_admin_files(self, admin_id: str, admin_secret: str) -> None:
        from datetime import datetime

        db_dir = os.path.dirname(os.path.abspath(str(self.db_path)))
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
            with safe_open(console_file_path, db_dir, "w", encoding="utf-8") as console_file:
                console_file.writelines(console_contents)
            logger.warning("Admin credentials saved to %s", sanitize_for_log(console_file_path))
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
                f.write(f'curl -H "Authorization: Bearer {admin_id}|{admin_secret}" \\\n+')
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
        # Ensure a superadmin exists. If none exists, create a bootstrap superadmin
        # account. This account has global admin privileges across tenants.
        if self.any_superadmin_exists():
            return
        import secrets

        super_id = "superadmin"
        while True:
            super_secret = secrets.token_urlsafe(32)
            if ":" not in super_secret and "|" not in super_secret:
                break
        if self.add_client(super_id, super_secret, "superadmin", "master"):
            try:
                self._write_admin_files(super_id, super_secret)
            except Exception as e:
                logger.error("Failed to create superadmin credential files: %s", str(e))
        else:
            logger.error("Failed to create superadmin user")


key_manager = KeyManager()
key_manager.ensure_admin_exists()
