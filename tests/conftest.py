import pytest

from backend.app.config import Settings


class FakeLLM:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def chat(self, messages, tools=None, **kw):
        self.calls.append(messages)
        item = self.script.pop(0)
        if callable(item):
            item = item(messages)
        return item

    async def health(self):
        return {"ok": True, "detail": "fake llm"}


def tool_call(call_id, name, args):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ],
    }


def final(text):
    return {"role": "assistant", "content": text, "tool_calls": None}


import json  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    return Settings(
        db_path=str(tmp_path / "nova-test.db"),
        log_dir=str(tmp_path / "logs"),
        llm_api_key="",
        llm_base_url="http://127.0.0.1:9/v1",
        autonomy_mode="autonomous",
        workspace_root=str(tmp_path / "workspace"),
        emergency_hotkey="ctrl+alt+shift+f12",
    )


@pytest.fixture
def svc(settings):
    from backend.app.services import build_services

    s = build_services(settings)
    yield s
    s.db.close()


@pytest.fixture
def client(settings):
    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    app = create_app(settings)
    with TestClient(app) as c:
        yield c, app
