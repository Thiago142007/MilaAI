import asyncio
import logging
import time
import uuid

from backend.app.events import EventBus

log = logging.getLogger("nova.security.confirmations")


class ConfirmationTimeout(Exception):
    pass


class ConfirmationService:
    def __init__(self, bus: EventBus, timeout_seconds: float = 180.0) -> None:
        self.bus = bus
        self.timeout_seconds = timeout_seconds
        self._pending: dict[str, asyncio.Future] = {}
        self._meta: dict[str, dict] = {}

    async def request(
        self,
        title: str,
        detail: str,
        risk: str = "medium",
        task_id: str | None = None,
    ) -> str:
        cid = uuid.uuid4().hex[:12]
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[cid] = fut
        meta = {
            "id": cid,
            "title": title,
            "detail": detail,
            "risk": risk,
            "task_id": task_id,
            "created_at": time.time(),
        }
        self._meta[cid] = meta
        await self.bus.publish("confirmation_request", meta)
        log.info("confirmation requested id=%s title=%s risk=%s", cid, title, risk)
        try:
            decision = await asyncio.wait_for(fut, timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            decision = "deny"
        finally:
            self._pending.pop(cid, None)
            self._meta.pop(cid, None)
        await self.bus.publish("confirmation_resolved", {"id": cid, "decision": decision})
        return decision

    def resolve(self, cid: str, decision: str) -> bool:
        fut = self._pending.get(cid)
        if fut is None or fut.done():
            return False
        if decision not in ("allow_once", "allow_task", "deny"):
            decision = "deny"
        fut.set_result(decision)
        return True

    def pending_list(self) -> list[dict]:
        return sorted(self._meta.values(), key=lambda m: m["created_at"])
