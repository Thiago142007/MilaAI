import json
import logging

from backend.app.db.database import Database, now
from backend.app.security.safety import redact_secrets

log = logging.getLogger("nova.audit")


class AuditLog:
    def __init__(self, db: Database) -> None:
        self.db = db

    def write(self, category: str, action: str, **detail) -> None:
        try:
            clean = {k: redact_secrets(str(v)) for k, v in detail.items()}
            self.db.execute(
                "INSERT INTO audit_log(ts, category, action, detail) VALUES(?,?,?,?)",
                (now(), category, action, json.dumps(clean, ensure_ascii=False)),
            )
        except Exception:
            log.exception("audit write failed")

    def fetch(self, limit: int = 100, offset: int = 0) -> list[dict]:
        rows = self.db.fetch_all(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?",
            (min(limit, 500), max(offset, 0)),
        )
        for r in rows:
            try:
                r["detail"] = json.loads(r.get("detail") or "{}")
            except Exception:
                pass
        return rows
