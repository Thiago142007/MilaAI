import asyncio
import itertools
import json
import time
from typing import Any

_ids = itertools.count(1)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self) -> tuple[int, asyncio.Queue]:
        async with self._lock:
            sid = next(_ids)
            q: asyncio.Queue = asyncio.Queue(maxsize=500)
            self._subscribers[sid] = q
            return sid, q

    async def unsubscribe(self, sid: int) -> None:
        async with self._lock:
            self._subscribers.pop(sid, None)

    async def publish(self, type_: str, payload: Any = None) -> None:
        message = {"type": type_, "payload": payload, "ts": time.time()}
        for q in list(self._subscribers.values()):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass

    def publish_nowait_safe(self, type_: str, payload: Any = None) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.publish(type_, payload))


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
