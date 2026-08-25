import asyncio
import json

import pytest

from backend.app.tools.base import Tool, ToolExecutor, ToolRegistry, fail, ok


class StubConfirmations:
    def __init__(self, answer="allow_once"):
        self.answer = answer
        self.requests = []

    async def request(self, title, detail, risk="medium", task_id=None):
        self.requests.append(risk)
        return self.answer


def make_pm(mode="manual"):
    import tempfile
    from pathlib import Path
    from backend.app.db.database import Database
    from backend.app.security.permissions import PermissionManager

    tmp = Path(tempfile.mkdtemp())
    return PermissionManager(Database(tmp / "x.db"), mode=mode)


def make_registry():
    reg = ToolRegistry()

    async def add(a: int, b: int):
        return ok(data={"sum": a + b})

    reg.register(
        Tool(
            name="math.add",
            description="adds",
            parameters={"properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]},
            handler=add,
        )
    )

    calls = []

    async def secret():
        calls.append(1)
        return ok(data="done")

    reg.register(
        Tool(
            name="guard.secret",
            description="needs permission",
            parameters={"properties": {}},
            handler=secret,
            permissions=["FILE_WRITE"],
            risk="medium",
        )
    )
    return reg, calls


async def test_unknown_tool():
    executor = ToolExecutor(make_registry()[0])
    r = await executor.run("nope.thing", {})
    assert not r["success"] and not r["recoverable"]


async def test_validation_errors():
    reg, _ = make_registry()
    executor = ToolExecutor(reg)
    r = await executor.run("math.add", {"a": 1})
    assert not r["success"] and "missing required" in r["error"]
    r = await executor.run("math.add", {"a": "x", "b": 2})
    assert not r["success"] and "must be integer" in r["error"]


async def test_success_and_timing():
    reg, _ = make_registry()
    executor = ToolExecutor(reg)
    r = await executor.run("math.add", {"a": 2, "b": 40})
    assert r["success"] and r["data"]["sum"] == 42
    assert "elapsed_ms" in r


async def test_permission_confirm_flow_allows_once():
    reg, calls = make_registry()
    conf = StubConfirmations("allow_once")
    pm = make_pm(mode="manual")
    executor = ToolExecutor(reg, permissions=pm, confirmations=conf)

    r = await executor.run("guard.secret", {})
    assert r["success"] and len(calls) == 1

    pm2 = make_pm(mode="manual")
    conf2 = StubConfirmations("deny")
    executor2 = ToolExecutor(reg, permissions=pm2, confirmations=conf2)
    r2 = await executor2.run("guard.secret", {}, task_id="t9")
    assert not r2["success"] and "denied" in r2["error"]
    assert len(calls) == 1


async def test_emergency_stop_blocks_execution():
    reg, calls = make_registry()
    stop = asyncio.Event()
    executor = ToolExecutor(reg, stop_event=stop)
    stop.set()
    r = await executor.run("math.add", {"a": 1, "b": 1})
    assert not r["success"]
    assert "emergency stop" in r["error"]


async def test_handler_crash_returns_structured_error():
    reg = ToolRegistry()

    async def boom():
        raise RuntimeError("kaboom")

    reg.register(
        Tool(
            name="chaos.boom",
            description="crashes",
            parameters={"properties": {}},
            handler=boom,
        )
    )
    executor = ToolExecutor(reg)
    r = await executor.run("chaos.boom", {})
    assert not r["success"]
    assert "kaboom" in r["error"] and r["recoverable"]
