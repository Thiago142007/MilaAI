import json
import time

from tests.conftest import FakeLLM, final


def test_ws_ping_pong(client):
    c, _ = client
    with c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_ws_chat_flow(client):
    c, app = client
    fake = FakeLLM([final("Resposta via websocket!")])
    app.state.services.llm = fake
    app.state.agent.llm = fake

    with c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat_message", "text": "oi pela ws", "conversation_id": "wstest1"})

        types = []
        for _ in range(25):
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg["type"] == "chat_final":
                assert msg["payload"]["content"] == "Resposta via websocket!"
                break
            if len(types) > 20:
                break
        assert "chat_accepted" in types
        assert "chat_final" in types


def test_ws_emergency_broadcast(client):
    c, _ = client
    with c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "emergency_stop"})
        got_emergency = False
        for _ in range(10):
            msg = ws.receive_json()
            if msg["type"] == "emergency":
                assert msg["payload"]["active"] is True
                got_emergency = True
                break
        assert got_emergency
        ws.send_json({"type": "reset_emergency"})
