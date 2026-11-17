import os
import sqlite3
import threading
import time
from pathlib import Path


class SQLiteStore:
    """Almacén SQLite compartido para tokens y sesiones temporales."""

    def __init__(self, database_path: str | None = None):
        configured_path = database_path or os.getenv(
            "SQLITE_DB_PATH",
            "data/api_marcaje.sqlite3",
        )
        self.database_path = Path(configured_path)
        if self.database_path.parent != Path("."):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = threading.Lock()
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=5,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize_schema(self) -> None:
        with self._schema_lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    jti TEXT PRIMARY KEY,
                    expires_at REAL NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expiration
                    ON refresh_tokens (expires_at);

                CREATE TABLE IF NOT EXISTS liveness_sessions (
                    session_id TEXT PRIMARY KEY,
                    owner TEXT,
                    flow TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_liveness_sessions_expiration
                    ON liveness_sessions (expires_at);
                """
            )

    def cleanup_expired(self) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM refresh_tokens WHERE expires_at <= ?",
                (now,),
            )
            connection.execute(
                "DELETE FROM liveness_sessions WHERE expires_at <= ?",
                (now,),
            )

    def check_health(self) -> bool:
        with self._connect() as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()
        return bool(result and result[0] == "ok")

    def register_refresh_token(self, jti: str, expires_at: int) -> None:
        self.cleanup_expired()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO refresh_tokens (jti, expires_at, revoked, created_at)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(jti) DO UPDATE SET
                    expires_at = excluded.expires_at,
                    revoked = 0
                """,
                (jti, expires_at, time.time()),
            )

    def is_refresh_token_active(self, jti: str, expires_at: int) -> bool:
        self.cleanup_expired()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM refresh_tokens
                WHERE jti = ?
                  AND expires_at = ?
                  AND revoked = 0
                  AND expires_at > ?
                """,
                (jti, expires_at, time.time()),
            ).fetchone()
        return row is not None

    def revoke_refresh_token(self, jti: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE refresh_tokens SET revoked = 1 WHERE jti = ?",
                (jti,),
            )

    def register_liveness_session(
        self,
        session_id: str,
        owner: str | None,
        flow: str,
        expires_at: float,
    ) -> None:
        self.cleanup_expired()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO liveness_sessions
                    (session_id, owner, flow, expires_at, used, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (session_id, owner, flow, expires_at, time.time()),
            )

    def consume_liveness_session(self, session_id: str) -> sqlite3.Row | None:
        self.cleanup_expired()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT session_id, owner, flow, expires_at, used
                FROM liveness_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if row is None or row["used"]:
                connection.rollback()
                return row
            connection.execute(
                """
                UPDATE liveness_sessions
                SET used = 1
                WHERE session_id = ? AND used = 0
                """,
                (session_id,),
            )
            connection.commit()
            return row


sqlite_store = SQLiteStore()
