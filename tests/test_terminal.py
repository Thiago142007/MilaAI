import pytest

from backend.app.tools.base import ToolRegistry
from backend.app.tools.builtin import terminal


class StubConfirmations:
    def __init__(self, answer="allow_once"):
        self.answer = answer
        self.requests = []

    async def request(self, title, detail, risk="medium", task_id=None):
        self.requests.append({"title": title, "risk": risk})
        return self.answer


class StubPermissions:
    mode = "manual"


@pytest.fixture
def tenv(tmp_path):
    conf = StubConfirmations()
    ctx = terminal.TerminalContext(tmp_path, conf, StubPermissions())
    reg = ToolRegistry()
    terminal.register_tools(reg, ctx)
    return ctx, conf, reg.get("terminal.execute").handler


async def test_safe_command_runs_without_confirmation(tenv):
    ctx, conf, handler = tenv
    r = await handler(command="echo nova-test-ok")
    assert r["success"]
    assert "nova-test-ok" in r["data"]["stdout"]
    assert conf.requests == []


async def test_warning_command_requires_confirmation(tenv):
    ctx, conf, handler = tenv
    r = await handler(command="del arquivo_inexistente.txt")
    assert len(conf.requests) == 1
    assert conf.requests[0]["risk"] == "warning"


async def test_denied_command_does_not_run(tenv):
    ctx, conf, handler = tenv
    conf.answer = "deny"
    r = await handler(command="taskkill /im explorer.exe")
    assert not r["success"]
    assert "denied" in r["error"]


async def test_dangerous_always_asks(tenv):
    ctx, conf, handler = tenv
    conf.answer = "deny"
    r = await handler(command="format Z:")
    assert not r["success"]
    assert conf.requests[0]["risk"] == "dangerous"
