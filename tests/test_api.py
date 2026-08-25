import json

from tests.conftest import FakeLLM, final, tool_call


def test_status_endpoint(client):
    c, app = client
    r = c.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["checks"]["tools"]["ok"]
    assert "autonomy_mode" in body


def test_tools_listing(client):
    c, _ = client
    tools = c.get("/api/tools").json()
    names = {t["name"] for t in tools}
    for expected in ["fs.read", "fs.write", "fs.delete", "terminal.execute", "web.search",
                     "screen.screenshot", "computer.click", "window.list", "apps.open"]:
        assert expected in names, expected


def test_permissions_endpoints(client):
    c, _ = client
    data = c.get("/api/permissions").json()
    assert data["mode"] in ("manual", "assisted", "autonomous")

    r = c.post("/api/permissions/mode", json={"mode": "banana"})
    assert r.status_code == 400

    r = c.post("/api/permissions/mode", json={"mode": "manual"})
    assert r.status_code == 200
    assert c.get("/api/permissions").json()["mode"] == "manual"


def test_emergency_stop_flow(client):
    c, app = client
    r = c.post("/api/emergency-stop")
    assert r.json()["stopped"] is True
    assert app.state.services.stop_event.is_set()
    status = c.get("/api/status").json()
    assert status["emergency_stopped"] is True
    c.post("/api/reset-emergency")
    assert not app.state.services.stop_event.is_set()


def test_screenshot_flow(client):
    c, _ = client
    r = c.post("/api/screenshot/capture")
    assert r.json()["success"] is True
    img = c.get("/api/screenshot")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/jpeg"
    assert len(img.content) > 1000


def test_memory_crud(client):
    c, _ = client
    mid = c.post("/api/memory", json={"content": "usuário prefere café"}).json()["id"]
    items = c.get("/api/memory").json()
    assert any(i["id"] == mid for i in items)
    assert c.delete(f"/api/memory/{mid}").status_code == 200
    assert c.delete(f"/api/memory/{mid}").status_code == 404


def test_chat_rest_with_fake_llm(client):
    c, app = client
    fake = FakeLLM([final("Resposta final de teste.")])
    app.state.services.llm = fake
    app.state.agent.llm = fake

    r = c.post("/api/chat", json={"text": "diga algo"})
    body = r.json()
    assert body["reply"] == "Resposta final de teste."
    task = c.get(f"/api/tasks/{body['task_id']}").json()
    assert task["status"] == "completed"


def test_task_cancel_endpoint(client):
    c, app = client
    fake = FakeLLM([tool_call("c1", "dummy.wait", {})])
    app.state.services.llm = fake
    app.state.agent.llm = fake

    async def wait_tool():
        import asyncio
        await asyncio.sleep(30)

    from backend.app.tools.base import Tool

    app.state.services.registry.register(
        Tool(name="dummy.wait", description="slow", parameters={"properties": {}}, handler=wait_tool)
    )
    app.state.agent.schemas = app.state.services.registry.openai_schemas()

    with c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat_message", "text": "espere"})
        tid = None
        for _ in range(10):
            msg = ws.receive_json()
            if msg["type"] == "chat_accepted":
                tid = msg["payload"]["task_id"]
                break
        assert tid

        ws.send_json({"type": "cancel_task", "task_id": tid})
        cancelled = False
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "task_update" and msg["payload"]["status"] == "cancelled":
                cancelled = True
                break
        assert cancelled
        r = c.post(f"/api/tasks/{tid}/cancel")
        assert r.status_code == 409


def test_settings_masked(client):
    c, _ = client
    s = c.get("/api/settings").json()
    assert "llm_model" in s
    assert isinstance(s.get("api_keys_configured"), int)
    assert "api_key" not in s
