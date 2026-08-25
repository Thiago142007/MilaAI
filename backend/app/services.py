from dataclasses import dataclass, field
from pathlib import Path

import asyncio
import logging

from backend.app.agent.context import ContextBuilder
from backend.app.agent.loop import NovaAgent
from backend.app.agent.task_manager import TaskManager
from backend.app.audit.audit import AuditLog
from backend.app.config import PROJECT_ROOT, Settings
from backend.app.db.database import Database
from backend.app.devices.manager import DeviceManager
from backend.app.events import EventBus
from backend.app.llm.client import LLMClient
from backend.app.memory.manager import MemoryManager
from backend.app.security.confirmations import ConfirmationService
from backend.app.security.permissions import PermissionManager
from backend.app.tools.base import ToolExecutor, ToolRegistry
from backend.app.tools.builtin import (
    apps,
    browser as browser_mod,
    control,
    devices as devices_tool_mod,
    filesystem,
    memory as memory_tool_mod,
    screen,
    terminal,
    voice as voice_tool_mod,
    websearch,
)
from backend.app.tools.builtin.browser import BrowserController
from backend.app.voice.manager import VoiceManager

log = logging.getLogger("nova.services")


@dataclass
class Services:
    settings: Settings
    db: Database
    bus: EventBus
    audit: AuditLog
    permissions: PermissionManager
    confirmations: ConfirmationService
    registry: ToolRegistry
    executor: ToolExecutor
    memory: MemoryManager
    tasks: TaskManager
    llm: LLMClient
    agent: NovaAgent
    browser: BrowserController
    screen_ctx: screen.ScreenContext
    voice: VoiceManager
    devices: DeviceManager
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    started_at: float = 0.0


def build_services(settings: Settings | None = None) -> Services:
    s = settings or Settings()

    db = Database(PROJECT_ROOT / s.db_path)
    bus = EventBus()
    audit = AuditLog(db)

    stored_mode = db.fetch_one("SELECT value FROM settings WHERE key='autonomy_mode'")
    mode = (stored_mode or {}).get("value") or s.autonomy_mode
    permissions = PermissionManager(db, mode=mode)
    confirmations = ConfirmationService(bus)

    registry = ToolRegistry()
    executor = ToolExecutor(
        registry,
        permissions=permissions,
        confirmations=confirmations,
        audit=audit,
        bus=bus,
    )

    workspace = s.workspace_path
    filesystem.register_tools(registry, filesystem.FsContext(workspace))
    terminal.register_tools(
        registry, terminal.TerminalContext(workspace, confirmations, permissions)
    )
    control.register_tools(registry)
    apps.register_tools(registry)

    data_dir = PROJECT_ROOT / "data"
    llm = LLMClient(
        base_url=s.llm_base_url,
        protocol=s.llm_protocol,
        api_keys=s.api_keys,
        model=s.llm_model,
        vision_model=s.vision_model,
        temperature=s.llm_temperature,
        max_tokens=s.llm_max_tokens,
        timeout_seconds=s.llm_timeout_seconds,
    )
    from backend.app.tools.builtin.screen import ScreenContext as _SC

    vision_ctx = _SC(data_dir, llm, s.vision_model)
    screen.register_tools(registry, vision_ctx)

    websearch.register_tools(registry, websearch.WebContext(s))

    browser = BrowserController(data_dir / "browser_profile")
    browser_mod.register_tools(registry, browser)

    voice_mgr = VoiceManager(data_dir / "voice")
    voice_tool_mod.register_tools(registry, voice_mgr)

    device_mgr = DeviceManager()
    devices_tool_mod.register_tools(registry, device_mgr)

    memory = MemoryManager(db)
    memory_tool_mod.register_tools(registry, memory)

    tasks = TaskManager(db, bus)
    context = ContextBuilder(memory, permissions.mode, str(workspace))
    stop_event = asyncio.Event()
    agent = NovaAgent(
        llm=llm,
        registry=registry,
        executor=executor,
        context=context,
        memory=memory,
        bus=bus,
        settings=s,
        stop_event=stop_event,
    )
    executor.stop_event = stop_event

    audit.write("system", "startup", mode=mode, tools=len(registry.all()))
    return Services(
        settings=s,
        db=db,
        bus=bus,
        audit=audit,
        permissions=permissions,
        confirmations=confirmations,
        registry=registry,
        executor=executor,
        memory=memory,
        tasks=tasks,
        llm=llm,
        agent=agent,
        browser=browser,
        screen_ctx=vision_ctx,
        voice=voice_mgr,
        devices=device_mgr,
        stop_event=stop_event,
        started_at=__import__("time").time(),
    )


class ChatRunner:
    def __init__(self, svcs: Services) -> None:
        self.svcs = svcs
        self.running: dict[str, asyncio.Task] = {}

    async def start_chat(self, text: str, conversation_id: str | None = None) -> dict:
        cid = self.svcs.memory.ensure_conversation(conversation_id)
        self.svcs.memory.add_message(cid, "user", text)

        if _maybe_remember(text):
            self.svcs.memory.remember(text, kind="user_fact", importance=0.7)

        task = self.svcs.tasks.create(description=text[:500], conversation_id=cid)
        task_id = task["id"]

        async def _run():
            try:
                reply = await self.svcs.agent.run(text, cid, task_id=task_id, tasks=self.svcs.tasks)
            except asyncio.CancelledError:
                await self.svcs.tasks.set_status(task_id, "cancelled")
                await self.svcs.bus.publish(
                    "chat_final",
                    {"conversation_id": cid, "task_id": task_id, "content": "[interrompido]"},
                )
                raise
            except Exception as exc:
                log.exception("agent crashed")
                await self.svcs.tasks.set_status(task_id, "failed", error=str(exc))
                await self.svcs.bus.publish(
                    "chat_error",
                    {"conversation_id": cid, "task_id": task_id, "error": str(exc)[:400]},
                )
            else:
                await self.svcs.bus.publish(
                    "chat_final",
                    {"conversation_id": cid, "task_id": task_id, "content": reply},
                )
                return reply
            finally:
                self.running.pop(task_id, None)

        self.running[task_id] = asyncio.get_running_loop().create_task(_run())
        return {"conversation_id": cid, "task_id": task_id}

    async def cancel_all(self) -> int:
        count = 0
        for tid, t in list(self.running.items()):
            if not t.done():
                t.cancel()
                count += 1
        return count

    def cancel_task(self, task_id: str) -> bool:
        t = self.running.get(task_id)
        if t and not t.done():
            t.cancel()
            return True
        return False


def _maybe_remember(text: str) -> bool:
    from backend.app.memory.manager import should_remember

    return should_remember(text)
