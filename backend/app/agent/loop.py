import asyncio
import hashlib
import json
import logging
from collections import Counter, deque
from typing import Any

from backend.app.agent.context import (
    ContextBuilder,
    make_assistant_envelope,
    make_tool_envelope,
)
from backend.app.events import EventBus
from backend.app.llm.client import LLMClient, LLMError
from backend.app.memory.manager import MemoryManager
from backend.app.tools.base import ToolExecutor, ToolRegistry

log = logging.getLogger("nova.agent")

MAX_RESULT_CHARS = 6000


class AgentStopped(Exception):
    pass


class BaseAgent:
    name: str = "base"

    async def run(
        self,
        user_text: str,
        conversation_id: str,
        task_id: str | None = None,
        tasks=None,
    ) -> str:
        raise NotImplementedError


class ResearchAgent(BaseAgent):
    name = "research-agent"

    def __init__(self, main_agent: "NovaAgent") -> None:
        self.main = main_agent

    async def run(self, user_text: str, conversation_id: str, task_id: str | None = None, tasks=None) -> str:
        enhanced_prompt = f"[RESEARCH TASK]: Focus on web search, information extraction and fact synthesis:\n{user_text}"
        return await self.main.run(enhanced_prompt, conversation_id, task_id=task_id, tasks=tasks)


class ComputerControlAgent(BaseAgent):
    name = "computer-agent"

    def __init__(self, main_agent: "NovaAgent") -> None:
        self.main = main_agent

    async def run(self, user_text: str, conversation_id: str, task_id: str | None = None, tasks=None) -> str:
        enhanced_prompt = f"[DESKTOP AUTOMATION TASK]: Focus on screen perception, window management and keyboard/mouse actions:\n{user_text}"
        return await self.main.run(enhanced_prompt, conversation_id, task_id=task_id, tasks=tasks)


class CodingAgent(BaseAgent):
    name = "coding-agent"

    def __init__(self, main_agent: "NovaAgent") -> None:
        self.main = main_agent

    async def run(self, user_text: str, conversation_id: str, task_id: str | None = None, tasks=None) -> str:
        enhanced_prompt = f"[CODING TASK]: Focus on code inspection, filesystem operations, and terminal execution:\n{user_text}"
        return await self.main.run(enhanced_prompt, conversation_id, task_id=task_id, tasks=tasks)


class DeviceAgent(BaseAgent):
    name = "device-agent"

    def __init__(self, main_agent: "NovaAgent") -> None:
        self.main = main_agent

    async def run(self, user_text: str, conversation_id: str, task_id: str | None = None, tasks=None) -> str:
        enhanced_prompt = f"[DEVICE TASK]: Focus on external devices, ESP32 sensors, and IoT commands:\n{user_text}"
        return await self.main.run(enhanced_prompt, conversation_id, task_id=task_id, tasks=tasks)


class NovaAgent(BaseAgent):
    name = "nova-main"

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        context: ContextBuilder,
        memory: MemoryManager,
        bus: EventBus,
        settings,
        stop_event: asyncio.Event,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.executor = executor
        self.context = context
        self.memory = memory
        self.bus = bus
        self.settings = settings
        self.stop_event = stop_event
        self.schemas = registry.openai_schemas()
        # Specialized sub-agents registry
        self.sub_agents: dict[str, BaseAgent] = {
            "research": ResearchAgent(self),
            "computer": ComputerControlAgent(self),
            "coding": CodingAgent(self),
            "devices": DeviceAgent(self),
        }

    async def run(
        self,
        user_text: str,
        conversation_id: str,
        task_id: str | None = None,
        tasks=None,
    ) -> str:
        max_steps = self.settings.agent_max_steps
        runtime_notes: list[str] = []
        action_counter: Counter = Counter()
        recent_actions: deque = deque(maxlen=4)

        await self.bus.publish("agent_state", {"state": "thinking", "task_id": task_id})

        for step in range(1, max_steps + 1):
            if self.stop_event.is_set():
                await self._finish(task_id, tasks, "failed", "emergency stop")
                return "Emergência acionada: interrompi a tarefa imediatamente."

            if tasks is not None and task_id:
                await tasks.wait_if_paused(task_id)
                if tasks.is_cancelled(task_id):
                    return "Tarefa cancelada pelo usuário."

            messages = self.context.build(
                conversation_id,
                runtime_notes=runtime_notes,
                task_description=user_text if step == 1 else None,
            )

            try:
                assistant = await self._chat_with_retry(messages)
            except LLMError as exc:
                log.error("LLM failed after retries: %s", exc)
                await self._finish(task_id, tasks, "failed", str(exc))
                return f"Não consegui consultar o modelo de IA: {exc}"

            tool_calls = assistant.get("tool_calls") or []
            if not tool_calls:
                final = (assistant.get("content") or "").strip()
                self.memory.add_message(conversation_id, "assistant", final)
                await self._finish(task_id, tasks, "completed", result=final)
                return final or "(sem resposta do modelo)"

            self.memory.add_message(
                conversation_id,
                "assistant",
                make_assistant_envelope(assistant.get("content"), tool_calls),
            )
            if tasks is not None and task_id:
                await tasks.set_status(task_id, "executing", progress=min(0.9, step / max_steps))

            for tc in tool_calls:
                if self.stop_event.is_set() or (tasks and task_id and tasks.is_cancelled(task_id)):
                    await self._finish(task_id, tasks, "failed", "stopped")
                    return "Execução interrompida."

                name = tc["function"]["name"]
                raw_args = tc["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                except json.JSONDecodeError:
                    args = {}
                    runtime_notes.append(f"Malformed JSON arguments for {name}: {raw_args[:200]}")

                key = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
                action_counter[key] += 1
                recent_actions.append(key)

                await self.bus.publish(
                    "tool_call",
                    {"name": name, "args": _safe_preview(args), "step": step, "task_id": task_id},
                )
                result = await self.executor.run(name, args, task_id=task_id)

                result_str = json.dumps(result, ensure_ascii=False, default=str)[:MAX_RESULT_CHARS]
                self.memory.add_message(
                    conversation_id,
                    "tool",
                    make_tool_envelope(tc["id"], result_str),
                )
                await self.bus.publish(
                    "tool_result",
                    {"name": name, "ok": bool(result.get("success")), "task_id": task_id},
                )

                if action_counter[key] >= self.settings.agent_loop_detection_threshold:
                    if action_counter[key] >= self.settings.agent_loop_detection_threshold + 2:
                        summary = _summarize_recent(recent_actions)
                        await self._finish(task_id, tasks, "failed", f"loop detected: {summary}")
                        return (
                            "Detectei que estava repetindo as mesmas ações sem progresso "
                            f"({summary}). Parei para evitar loops. Sugiro revisar a abordagem."
                        )
                    runtime_notes.append(
                        f"Action '{name}' was already executed {action_counter[key]} times with identical arguments. Change strategy."
                    )

        await self._finish(task_id, tasks, "failed", "max steps reached")
        return (
            f"Atingi o limite de {max_steps} passos sem concluir totalmente. "
            "Posso continuar de onde parei se você pedir."
        )

    async def _chat_with_retry(self, messages: list[dict]) -> dict:
        delay = 0.05 if getattr(self.settings, "test_mode", False) or getattr(self.settings, "log_level", "") == "DEBUG" else 1.0
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return await self.llm.chat(messages, tools=self.schemas)
            except LLMError as exc:
                last_exc = exc
                if getattr(exc, "status", None) in (400, 401, 403, 404):
                    raise
                log.warning("LLM attempt %d failed: %s", attempt + 1, exc)
                await asyncio.sleep(delay)
                delay *= 2
        raise last_exc  # type: ignore[misc]

    async def _finish(self, task_id, tasks, status: str, error: str | None = None, result: str | None = None):
        if tasks is not None and task_id:
            try:
                await tasks.set_status(task_id, status, error=error, result=result)
            except Exception:
                log.exception("failed to finalize task %s", task_id)
        await self.bus.publish("agent_state", {"state": "idle" if status == "completed" else "error", "task_id": task_id})


def _safe_preview(args: dict) -> dict:
    out = {}
    for k, v in list(args.items())[:8]:
        s = str(v)
        out[k] = s[:120] + ("…" if len(s) > 120 else "")
    return out


def _summarize_recent(actions: deque) -> str:
    try:
        names = [a.split(":")[0] for a in list(actions)[-3:]]
        return ", ".join(names)
    except Exception:
        return "repeated actions"


def action_hash(name: str, args: dict) -> str:
    return hashlib.sha256(f"{name}:{json.dumps(args, sort_keys=True)}".encode()).hexdigest()[:16]


_ = Any
