import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations(
  id TEXT PRIMARY KEY,
  title TEXT,
  created_at REAL
);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id TEXT,
  role TEXT,
  content TEXT,
  created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY,
  description TEXT,
  status TEXT,
  progress REAL,
  result TEXT,
  error TEXT,
  conversation_id TEXT,
  created_at REAL,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS task_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT,
  type TEXT,
  payload TEXT,
  created_at REAL
);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL,
  category TEXT,
  action TEXT,
  detail TEXT
);
CREATE TABLE IF NOT EXISTS memories(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT,
  content TEXT,
  importance REAL,
  created_at REAL
);
CREATE TABLE IF NOT EXISTS grants(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT,
  scope TEXT,
  task_id TEXT,
  created_at REAL
);
CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            if sql.lstrip().upper().startswith(("INSERT", "REPLACE")):
                return cur.lastrowid or cur.rowcount
            return max(cur.rowcount, 0)

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def health(self) -> bool:
        return self.fetch_one("SELECT 1 AS ok")["ok"] == 1


def now() -> float:
    return time.time()
