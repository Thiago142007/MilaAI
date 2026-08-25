import logging

from backend.app.db.database import Database, now

log = logging.getLogger("nova.security.permissions")

CATEGORIES = [
    "SCREEN_READ",
    "FILE_READ",
    "FILE_WRITE",
    "FILE_DELETE",
    "TERMINAL",
    "WEB",
    "MOUSE_CONTROL",
    "KEYBOARD_CONTROL",
    "APPLICATION_CONTROL",
    "DEVICE_CONTROL",
]

MODE_POLICY = {
    "manual": {"SCREEN_READ", "FILE_READ"},
    "assisted": {"SCREEN_READ", "FILE_READ", "WEB", "MOUSE_CONTROL", "KEYBOARD_CONTROL"},
    "autonomous": set(CATEGORIES) - {"FILE_DELETE"},
}

ALWAYS_CONFIRM = {"FILE_DELETE"}


class Decision:
    def __init__(self, action: str, reason: str = "") -> None:
        self.action = action
        self.reason = reason

    @property
    def allowed(self) -> bool:
        return self.action == "allow"

    def to_dict(self) -> dict:
        return {"action": self.action, "reason": self.reason}


class PermissionManager:
    def __init__(self, db: Database, mode: str = "assisted") -> None:
        if mode not in MODE_POLICY:
            mode = "assisted"
        self.db = db
        self.mode = mode
        self._session_grants: dict[str, int] = {}

    def decide(self, category: str, task_id: str | None = None) -> Decision:
        if category not in CATEGORIES:
            return Decision("deny", f"unknown category {category}")
        if self._has_task_grant(category, task_id):
            return Decision("allow", "task grant")
        if self._session_grants.get(category, 0) > 0:
            return Decision("allow", "session grant")
        if category in ALWAYS_CONFIRM:
            return Decision("confirm", f"{category} always requires confirmation")
        if category in MODE_POLICY[self.mode]:
            return Decision("allow", f"auto-allowed by mode {self.mode}")
        return Decision(
            "confirm",
            f"{category} requires confirmation in mode {self.mode}",
        )

    async def apply_decision(self, decision_result: str, category: str, task_id: str | None = None) -> None:
        if decision_result == "allow_once":
            self.consume_once(category)
        elif decision_result == "allow_task":
            self.add_task_grant(category, task_id or "")

    def add_task_grant(self, category: str, task_id: str) -> None:
        self.db.execute(
            "INSERT INTO grants(category, scope, task_id, created_at) VALUES(?,?,?,?)",
            (category, "task", task_id, now()),
        )
        log.info("grant added category=%s scope=task task=%s", category, task_id)

    def add_session_grant(self, category: str) -> None:
        self._session_grants[category] = self._session_grants.get(category, 0) + 1

    def consume_once(self, category: str) -> None:
        pass

    def _has_task_grant(self, category: str, task_id: str | None) -> bool:
        if not task_id:
            return False
        row = self.db.fetch_one(
            "SELECT id FROM grants WHERE category=? AND scope='task' AND task_id=? LIMIT 1",
            (category, task_id),
        )
        return row is not None

    def clear_task_grants(self, task_id: str) -> None:
        self.db.execute("DELETE FROM grants WHERE task_id=?", (task_id,))

    def reset_session(self) -> None:
        self._session_grants.clear()
        self.db.execute("DELETE FROM grants WHERE scope='session'")

    def set_mode(self, mode: str) -> bool:
        if mode not in MODE_POLICY:
            return False
        self.mode = mode
        self.db.execute(
            "INSERT INTO settings(key,value) VALUES('autonomy_mode',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (mode,),
        )
        log.info("autonomy mode set to %s", mode)
        return True

    def status(self) -> list[dict]:
        out = []
        for c in CATEGORIES:
            d = self.decide(c)
            out.append({"category": c, "auto_allowed": d.allowed})
        return out
