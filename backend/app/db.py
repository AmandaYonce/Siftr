import sqlite3
from pathlib import Path

# Bumping the version drops the photos table, forcing a clean re-scan.
# The database is purely a cache, so nothing of value is lost.
_SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    mtime REAL NOT NULL,
    size INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    taken_at TEXT,
    phash TEXT NOT NULL,
    sharpness REAL NOT NULL,
    face_count INTEGER NOT NULL,
    face_sharpness REAL NOT NULL,
    thumb_path TEXT NOT NULL
)
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version != _SCHEMA_VERSION:
        conn.execute("DROP TABLE IF EXISTS photos")
        conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
    conn.execute(_SCHEMA)
    conn.commit()
    return conn
