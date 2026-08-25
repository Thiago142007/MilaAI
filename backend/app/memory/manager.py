import json
import logging
import re
import uuid

from backend.app.db.database import Database, now

log = logging.getLogger("nova.memory")

HISTORY_LIMIT = 24

REMEMBER_HINTS = [
    r"\b(lembre|lembra|n[aã]o esque|remember)\b",
    r"\bmeu nome [eé]\b",
    r"\bme chamo\b",
    r"\beu (prefiro|gosto|odeio)\b",
    r"\bminha (conta|senha|configura|[a-z]+ favorita)",
    r"\bsempre que eu disser\b",
]


def should_remember(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pat, lowered) for pat in REMEMBER_HINTS)


class MemoryManager:
    """Manages short-term context, conversation history, long-term memory, and procedural memories."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def ensure_conversation(self, conversation_id: str | None = None, title: str = "Chat") -> str:
        cid = conversation_id or uuid.uuid4().hex[:12]
        existing = self.db.fetch_one(
            "SELECT id FROM conversations WHERE id=?", (cid,)
        )
        if not existing:
            self.db.execute(
                "INSERT INTO conversations(id, title, created_at) VALUES(?,?,?)",
                (cid, title, now()),
            )
        return cid

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        self.db.execute(
            "INSERT INTO messages(conversation_id, role, content, created_at) VALUES(?,?,?,?)",
            (conversation_id, role, content[:100_000], now()),
        )

    def get_messages(self, conversation_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
        rows = self.db.fetch_all(
            "SELECT role, content FROM messages WHERE conversation_id=? "
            "ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        )
        return list(reversed(rows))

    def list_conversations(self, limit: int = 50) -> list[dict]:
        return self.db.fetch_all(
            "SELECT c.*, COUNT(m.id) AS message_count FROM conversations c "
            "LEFT JOIN messages m ON m.conversation_id=c.id "
            "GROUP BY c.id ORDER BY c.created_at DESC LIMIT ?",
            (limit,),
        )

    def remember(self, content: str, kind: str = "fact", importance: float = 0.5) -> int:
        return self.db.execute(
            "INSERT INTO memories(kind, content, importance, created_at) VALUES(?,?,?,?)",
            (kind, content[:5000], importance, now()),
        )

    def recall(self, query: str, k: int = 5) -> list[dict]:
        words = [w for w in re.findall(r"[a-z0-9]{3,}", query.lower())][:8]
        if not words:
            return []
        conditions = " OR ".join(["content LIKE ?"] * len(words))
        params = [f"%{w}%" for w in words] + [k]
        rows = self.db.fetch_all(
            f"SELECT * FROM memories WHERE {conditions} "
            "ORDER BY importance DESC, created_at DESC LIMIT ?",
            tuple(params),
        )
        return rows

    def list_memories(self, limit: int = 200, kind: str | None = None) -> list[dict]:
        if kind:
            return self.db.fetch_all(
                "SELECT * FROM memories WHERE kind=? ORDER BY created_at DESC LIMIT ?",
                (kind, limit),
            )
        return self.db.fetch_all(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)
        )

    def delete_memory(self, memory_id: int) -> bool:
        count = self.db.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        return count > 0

    def save_procedure(self, name: str, steps: list[str], description: str = "") -> int:
        payload = json.dumps({"name": name, "steps": steps, "description": description})
        return self.db.execute(
            "INSERT INTO memories(kind, content, importance, created_at) VALUES(?,?,?,?)",
            ("procedure", payload, 0.85, now()),
        )

    def get_procedure(self, name: str) -> dict | None:
        rows = self.db.fetch_all(
            "SELECT * FROM memories WHERE kind='procedure' ORDER BY created_at DESC LIMIT 100"
        )
        target = name.lower().strip()
        for r in rows:
            data = _json_loads_safe(r["content"])
            if data and (target in data.get("name", "").lower() or data.get("name", "").lower() in target):
                return data
        return None

    def list_procedures(self) -> list[dict]:
        rows = self.db.fetch_all(
            "SELECT * FROM memories WHERE kind='procedure' ORDER BY created_at DESC LIMIT 100"
        )
        procs = []
        for r in rows:
            data = _json_loads_safe(r["content"])
            if data:
                data["id"] = r["id"]
                data["created_at"] = r["created_at"]
                procs.append(data)
        return procs


def _json_loads_safe(text):
    try:
        return json.loads(text)
    except Exception:
        return None
