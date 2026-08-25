import json

import pytest

from backend.app.memory.manager import MemoryManager, should_remember


@pytest.fixture
def mem(tmp_path):
    from backend.app.db.database import Database

    return MemoryManager(Database(tmp_path / "m.db"))


async def test_conversation_roundtrip(mem):
    cid = mem.ensure_conversation()
    mem.add_message(cid, "user", "olá")
    mem.add_message(cid, "assistant", "oi!")
    msgs = mem.get_messages(cid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]


async def test_history_limit_order(mem):
    cid = mem.ensure_conversation()
    for i in range(30):
        mem.add_message(cid, "user", f"msg {i}")
    msgs = mem.get_messages(cid, limit=10)
    assert len(msgs) == 10
    assert msgs[0]["content"] == "msg 20"
    assert msgs[-1]["content"] == "msg 29"


async def test_recall_by_keywords(mem):
    mem.remember("usuário gosta de café", importance=0.9)
    mem.remember("servidor minecraft fica na porta 25565")
    rows = mem.recall("qual café você recomenda?")
    assert any("café" in r["content"] for r in rows)
    rows2 = mem.recall("minecraft server port")
    assert any("minecraft" in r["content"].lower() for r in rows2)


def test_should_remember_heuristic():
    assert should_remember("lembre que meu servidor usa a porta 25565")
    assert should_remember("meu nome é Bruno")
    assert should_remember("remember that I prefer dark mode")
    assert not should_remember("que horas são?")


async def test_delete_memory(mem):
    mid = mem.remember("temporário")
    assert mem.delete_memory(mid)
    assert not mem.delete_memory(mid)
