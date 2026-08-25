import json

import pytest

from tests.conftest import FakeLLM, final, tool_call
from backend.app.tools.base import Tool, ok


async def test_agent_executes_tool_then_finishes(svc, tmp_path):
    svc.llm = FakeLLM([
        tool_call("c1", "fs.write", {"path": "note.txt", "content": "olá nova"}),
        final("Feito! O arquivo note.txt foi criado."),
    ])
    svc.agent.llm = svc.llm

    cid = svc.memory.ensure_conversation()
    svc.memory.add_message(cid, "user", "crie o arquivo note.txt")
    reply = await svc.agent.run("crie o arquivo note.txt", cid)

    assert "Feito" in reply
    assert (tmp_path / "workspace" / "note.txt").read_text(encoding="utf-8") == "olá nova"

    msgs = svc.memory.get_messages(cid)
    roles = [m["role"] for m in msgs]
    assert roles == ["user", "assistant", "tool", "assistant"]
    tool_msg = json.loads(msgs[2]["content"])
    assert tool_msg["tool_call_id"] == "c1"


async def test_agent_task_lifecycle_completed(svc):
    svc.llm = FakeLLM([final("resposta direta")])
    svc.agent.llm = svc.llm

    task = svc.tasks.create(description="diga oi", conversation_id=None)
    cid = svc.memory.ensure_conversation()
    await svc.agent.run("diga oi", cid, task_id=task["id"], tasks=svc.tasks)

    done = svc.tasks.get(task["id"])
    assert done["status"] == "completed"
    assert "resposta direta" in done["result"]


async def test_loop_detection_stops_repetition(svc):
    for _ in range(6):
        pass

    async def ping():
        return ok(data={"pong": True})

    svc.registry.register(
        Tool(
            name="dummy.ping",
            description="test tool",
            parameters={"properties": {}},
            handler=ping,
        )
    )
    svc.agent.schemas = svc.registry.openai_schemas()

    script = [tool_call(f"c{i}", "dummy.ping", {}) for i in range(5)]
    svc.llm = FakeLLM(script + [final("nunca deve chegar aqui")])
    svc.agent.llm = svc.llm

    cid = svc.memory.ensure_conversation()
    reply = await svc.agent.run("faça ping repetidamente", cid)

    assert "repetindo" in reply or "loop" in reply.lower()


async def test_cancelled_task_returns_message(svc):
    svc.llm = FakeLLM([tool_call("c1", "fs.list", {"path": "."}), final("x")])
    svc.agent.llm = svc.llm

    task = svc.tasks.create(description="listar", conversation_id=None)
    cid = svc.memory.ensure_conversation()
    await svc.tasks.cancel(task["id"])

    reply = await svc.agent.run("liste arquivos", cid, task_id=task["id"], tasks=svc.tasks)
    assert "cancelada" in reply.lower()


async def test_llm_error_reported_gracefully(svc):
    class ExplodingLLM:
        async def chat(self, *a, **k):
            raise Exception("boom http 500")

        async def health(self):
            return {"ok": False}

    from backend.app.llm.client import LLMError

    class AlwaysFail:
        status = None
        calls = 0

        async def chat(self, messages, tools=None, **kw):
            AlwaysFail.calls += 1
            raise LLMError("endpoint down")

        async def health(self):
            return {"ok": False, "detail": "down"}

    svc.llm = AlwaysFail()
    svc.agent.llm = svc.llm

    cid = svc.memory.ensure_conversation()
    reply = await svc.agent.run("oi", cid)
    assert "Não consegui consultar o modelo" in reply
