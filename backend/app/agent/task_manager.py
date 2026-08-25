import asyncio
import logging
import uuid

from backend.app.db.database import Database, now
from backend.app.events import EventBus

log = logging.getLogger("nova.tasks")

STATUSES = [
    "queued",
    "planning",
    "executing",
    "waiting_confirmation",
    "completed",
    "failed",
    "cancelled",
]


class TaskManager:
    def __init__(self, db: Database, bus: EventBus) -> None:
        self.db = db
        self.bus = bus
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._pause_events: dict[str, asyncio.Event] = {}

    def create(self, description: str, conversation_id: str | None = None) -> dict:
        task_id = uuid.uuid4().hex[:12]
        ts = now()
        self.db.execute(
            "INSERT INTO tasks(id, description, status, progress, conversation_id, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (task_id, description[:2000], "queued", 0.0, conversation_id, ts, ts),
        )
        task = self.get(task_id)
        self.bus.publish_nowait_safe("task_update", task)
        return task

    def get(self, task_id: str) -> dict | None:
        return self.db.fetch_one("SELECT * FROM tasks WHERE id=?", (task_id,))

    def list(self, limit: int = 100) -> list[dict]:
        return self.db.fetch_all(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        )

    async def set_status(
        self,
        task_id: str,
        status: str,
        progress: float | None = None,
        error: str | None = None,
        result: str | None = None,
    ) -> None:
        fields = ["status=?", "updated_at=?"]
        params: list = [status, now()]
        if progress is not None:
            fields.append("progress=?")
            params.append(round(max(0.0, min(progress, 1.0)), 3))
        if error is not None:
            fields.append("error=?")
            params.append(error[:2000])
        if result is not None:
            fields.append("result=?")
            params.append(result[:10000])
        params.append(task_id)
        self.db.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id=?", tuple(params))
        if status in ("completed", "failed", "cancelled"):
            self.clear_cancel_event(task_id)
        await self.bus.publish("task_update", self.get(task_id))

    def add_event(self, task_id: str, type_: str, payload: dict) -> None:
        import json

        self.db.execute(
            "INSERT INTO task_events(task_id, type, payload, created_at) VALUES(?,?,?,?)",
            (task_id, type_, json.dumps(payload, ensure_ascii=False, default=str)[:8000], now()),
        )

    def events(self, task_id: str) -> list[dict]:
        rows = self.db.fetch_all(
            "SELECT * FROM task_events WHERE task_id=? ORDER BY id", (task_id,)
        )
        import json

        for r in rows:
            try:
                r["payload"] = json.loads(r["payload"])
            except Exception:
                pass
        return rows

    def cancel_event(self, task_id: str) -> asyncio.Event:
        if task_id not in self._cancel_events:
            self._cancel_events[task_id] = asyncio.Event()
        return self._cancel_events[task_id]

    def clear_cancel_event(self, task_id: str) -> None:
        self._cancel_events.pop(task_id, None)
        self._pause_events.pop(task_id, None)

    async def cancel(self, task_id: str) -> bool:
        task = self.get(task_id)
        if not task or task["status"] in ("completed", "failed", "cancelled"):
            return False
        self.cancel_event(task_id).set()
        self._pause_events.pop(task_id, None)
        await self.set_status(task_id, "cancelled")
        log.info("task %s cancelled", task_id)
        return True

    def is_cancelled(self, task_id: str) -> bool:
        ev = self._cancel_events.get(task_id)
        if ev and ev.is_set():
            return True
        task = self.get(task_id)
        return bool(task and task["status"] == "cancelled")

    def pause(self, task_id: str) -> None:
        if task_id not in self._pause_events:
            self._pause_events[task_id] = asyncio.Event()

    async def resume(self, task_id: str) -> None:
        ev = self._pause_events.get(task_id)
        if ev:
            ev.set()
        await asyncio.sleep(0)

    def is_paused(self, task_id: str) -> bool:
        ev = self._pause_events.get(task_id)
        return bool(ev and not ev.is_set())

    async def wait_if_paused(self, task_id: str) -> None:
        while self.is_paused(task_id) and not self.is_cancelled(task_id):
            await asyncio.sleep(0.4)
