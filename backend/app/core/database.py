"""SQLite persistent database storage with transactional mutations and audit logging."""
import sqlite3
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.core.config import get_settings

_lock = threading.Lock()


def utc_now() -> str:
    """Return current ISO8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        self.db_path = db_path or settings.database_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def init_db(self) -> None:
        with _lock, self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS specs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    format TEXT NOT NULL,
                    raw_spec TEXT NOT NULL,
                    endpoints_summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS fuzz_jobs (
                    id TEXT PRIMARY KEY,
                    spec_id TEXT NOT NULL,
                    target_base_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config TEXT NOT NULL,
                    total_cases INTEGER NOT NULL DEFAULT 0,
                    passed_cases INTEGER NOT NULL DEFAULT 0,
                    findings_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    triggered_by TEXT NOT NULL,
                    FOREIGN KEY(spec_id) REFERENCES specs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS test_cases (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    endpoint_method TEXT NOT NULL,
                    endpoint_path TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    request_payload TEXT NOT NULL,
                    expected_status INTEGER NOT NULL,
                    generated_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES fuzz_jobs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS test_results (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    status_code INTEGER,
                    latency_ms REAL NOT NULL,
                    response_body TEXT,
                    error_message TEXT,
                    severity TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    reproduction_curl TEXT NOT NULL,
                    advisory_notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
                    FOREIGN KEY(job_id) REFERENCES fuzz_jobs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_spec ON fuzz_jobs(spec_id);
                CREATE INDEX IF NOT EXISTS idx_cases_job ON test_cases(job_id);
                CREATE INDEX IF NOT EXISTS idx_results_job ON test_results(job_id);
                CREATE INDEX IF NOT EXISTS idx_results_severity ON test_results(severity);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
            """)
            conn.commit()

    def record_audit(self, user_id: str, action: str, resource: str, details: Dict[str, Any]) -> None:
        """Record an immutable audit log entry."""
        import uuid
        with _lock, self.get_connection() as conn:
            conn.execute(
                "INSERT INTO audit_logs (id, timestamp, user_id, action, resource, details) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), utc_now(), user_id, action, resource, json.dumps(details))
            )
            conn.commit()


_db_instance: Optional[Database] = None


def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
