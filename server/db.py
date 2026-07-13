"""SQLite database initialization and connection helpers."""

import os
import sqlite3
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "hexstrike.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL,
    completed_at TEXT,
    config_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS scan_jobs (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    params_json TEXT NOT NULL DEFAULT '{}',
    stdout TEXT,
    stderr TEXT,
    return_code INTEGER,
    execution_time REAL,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    job_id TEXT,
    severity TEXT NOT NULL DEFAULT 'info',
    title TEXT NOT NULL,
    description TEXT,
    evidence TEXT,
    tool_name TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES scan_jobs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at);
CREATE INDEX IF NOT EXISTS idx_scan_jobs_scan_id ON scan_jobs(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_scan_id ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_reports_scan_id ON reports(scan_id);
"""


def get_db_path() -> Path:
    env_path = os.environ.get("HEXSTRIKE_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(findings)").fetchall()}
    if "tool_name" not in cols:
        conn.execute("ALTER TABLE findings ADD COLUMN tool_name TEXT")


def init_db(db_path: Optional[Path] = None) -> Path:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate(conn)
        conn.commit()
    return path


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    if not path.exists():
        init_db(path)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def check_db_health() -> dict:
    try:
        path = get_db_path()
        if not path.exists():
            init_db(path)
        with get_connection(path) as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "path": str(path)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
