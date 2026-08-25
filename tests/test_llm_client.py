import json

import httpx
import pytest

from backend.app.llm.client import LLMClient, LLMError


def openai_body(content="ok"):
    return {"choices": [{"message": {"role": "assistant", "content": content, "tool_calls": None}}]}


def test_multi_key_failover_on_429():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        if auth.endswith("key1") or auth.endswith("key2"):
            calls["n"] += 1
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json=openai_body("done"))

    client = LLMClient(
        base_url="https://x.example/v1",
        api_keys=["key1", "key2", "key3"],
        transport=httpx.MockTransport(handler),
    )
    import asyncio

    result = asyncio.run(client.chat([{"role": "user", "content": "hi"}]))
    assert result["content"] == "done"
    assert client.key_failovers >= 2


def test_all_keys_rejected_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    client = LLMClient(
        base_url="https://x.example/v1",
        api_keys=["k1", "k2"],
        transport=httpx.MockTransport(handler),
    )
    import asyncio

    with pytest.raises(LLMError) as exc:
        asyncio.run(client.chat([{"role": "user", "content": "hi"}]))
    assert "all configured API keys" in str(exc.value)
    assert exc.value.status == 401


def test_round_robin_distributes_keys():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("Authorization"))
        return httpx.Response(200, json=openai_body())

    client = LLMClient(
        base_url="https://x.example/v1",
        api_keys=["a", "b"],
        transport=httpx.MockTransport(handler),
    )
    import asyncio

    for _ in range(4):
        asyncio.run(client.chat([{"role": "user", "content": "x"}]))
    assert len(seen) == 4
    assert any(h.endswith("a") for h in seen) and any(h.endswith("b") for h in seen)


def test_single_key_no_rotation_on_429():
    count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        count["n"] += 1
        return httpx.Response(429, text="slow down")

    client = LLMClient(
        base_url="https://x.example/v1",
        api_keys=["only-key"],
        transport=httpx.MockTransport(handler),
    )
    import asyncio

    with pytest.raises(LLMError):
        asyncio.run(client.chat([{"role": "user", "content": "hi"}]))
    assert count["n"] == 1


def test_ollama_protocol_tool_call_roundtrip():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        body = json.loads(request.content.decode())
        captured["body"] = body
        return httpx.Response(
            200,
            json={
                "model": "minimax-m3:cloud",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "fs.list",
                                "arguments": {"path": "."},
                            }
                        }
                    ],
                },
                "done": True,
            },
        )

    client = LLMClient(
        base_url="https://ollama.com",
        protocol="ollama",
        api_keys=["cloudkey"],
        model="minimax-m3:cloud",
        transport=httpx.MockTransport(handler),
    )

    messages = [
        {"role": "system", "content": "sys"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "veja a tela"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}},
            ],
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "screen.screenshot", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": '{"success": true}'},
    ]
    tools = [
        {
            "type": "function",
            "function": {"name": "t", "description": "d", "parameters": {"properties": {}}},
        }
    ]

    import asyncio

    result = asyncio.run(client.chat(messages, tools=tools))

    assert captured["url"].endswith("/api/chat")
    assert captured["auth"] == "Bearer cloudkey"
    sent = captured["body"]
    assert sent["model"] == "minimax-m3:cloud"
    assert sent["stream"] is False
    user_msg = sent["messages"][1]
    assert user_msg["images"] == ["QUJD"]
    assert "veja a tela" in user_msg["content"]
    assistant_msg = sent["messages"][2]
    assert isinstance(assistant_msg["tool_calls"][0]["function"]["arguments"], dict)
    tool_msg = sent["messages"][3]
    assert "tool_call_id" not in tool_msg
    assert sent["tools"][0]["function"]["name"] == "t"

    assert result["tool_calls"][0]["function"]["name"] == "fs.list"
    parsed_args = json.loads(result["tool_calls"][0]["function"]["arguments"])
    assert parsed_args == {"path": "."}


def test_health_ollama_tags():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        return httpx.Response(404)

    client = LLMClient(
        base_url="https://ollama.com",
        protocol="ollama",
        api_keys=["k"],
        model="minimax-m3:cloud",
        transport=httpx.MockTransport(handler),
    )
    import asyncio

    health = asyncio.run(client.health())
    assert health["ok"] is True
    assert "minimax-m3:cloud" in health["detail"]
