import asyncio
import itertools
import json
import logging

import httpx

log = logging.getLogger("nova.llm")

ROTATE_ON_STATUS = (401, 403, 429)


class LLMError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _to_ollama_messages(messages: list[dict]) -> list[dict]:
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")

        if isinstance(content, list):
            texts, images = [], []
            for part in content:
                if part.get("type") == "text":
                    texts.append(part["text"])
                elif part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if "base64," in url:
                        images.append(url.split("base64,", 1)[1])
            msg = {"role": role, "content": "\n".join(texts)}
            if images:
                msg["images"] = images
            out.append(msg)
            continue

        if role == "assistant" and m.get("tool_calls"):
            tool_calls = []
            for tc in m["tool_calls"]:
                fn = tc["function"]
                args = fn.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append({"function": {"name": fn["name"], "arguments": args}})
            out.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
            continue

        if role == "tool":
            out.append({"role": "tool", "content": str(content or "")})
            continue

        out.append({"role": role, "content": content})
    return out


def _from_ollama_response(data: dict) -> dict:
    msg = data.get("message", {}) or {}
    tool_calls = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        fn = tc.get("function", {}) or {}
        args = fn.get("arguments")
        if not isinstance(args, str):
            args = json.dumps(args or {}, ensure_ascii=False)
        tool_calls.append(
            {
                "id": f"call_{data.get('created_at', '')}_{i}",
                "type": "function",
                "function": {"name": fn.get("name"), "arguments": args},
            }
        )
    return {
        "role": "assistant",
        "content": msg.get("content"),
        "tool_calls": tool_calls or None,
    }


class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        protocol: str = "openai",
        model: str = "",
        vision_model: str = "",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout_seconds: float = 120.0,
        api_keys: list[str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.protocol = protocol if protocol in ("openai", "ollama") else "openai"
        self.api_keys = [k for k in (api_keys or []) if k] or ([api_key] if api_key else [])
        self.model = model
        self.vision_model = vision_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self._key_cycle = itertools.cycle(range(max(len(self.api_keys), 1)))
        self.total_requests = 0
        self.key_failovers = 0

    @property
    def current_key_index(self) -> int:
        return next(self._key_cycle)

    def _auth_headers(self) -> dict:
        if not self.api_keys:
            return {}
        key = self.api_keys[self.current_key_index % len(self.api_keys)]
        return {"Authorization": f"Bearer {key}"}

    async def _post(self, url: str, payload: dict) -> httpx.Response:
        headers = {"Content-Type": "application/json", **self._auth_headers()}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
            return await client.post(url, json=payload, headers=headers)

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        attempts = max(len(self.api_keys), 1)
        last_status: int | None = None
        last_body = ""

        for attempt in range(attempts):
            if attempt > 0:
                self.key_failovers += 1
                log.warning(
                    "rotating API key (%d/%d) after status %s",
                    attempt + 1,
                    attempts,
                    last_status,
                )
            resp = await self._send(messages, tools, model, temperature, max_tokens)
            if resp.status_code in ROTATE_ON_STATUS and attempt < attempts - 1 and len(self.api_keys) > 1:
                last_status = resp.status_code
                last_body = resp.text[:300]
                continue
            return self._parse(resp)
        raise LLMError(f"LLM API error {last_status}: {last_body}", status=last_status)

    async def _send(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> httpx.Response:
        self.total_requests += 1
        chosen_model = model or self.model
        temperature = self.temperature if temperature is None else temperature
        max_tokens = self.max_tokens if max_tokens is None else max_tokens

        if self.protocol == "ollama":
            payload: dict = {
                "model": chosen_model,
                "messages": _to_ollama_messages(messages),
                "stream": False,
                "options": {"temperature": temperature},
            }
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            if tools:
                payload["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"],
                        },
                    }
                    for t in tools
                ]
            return await self._post(f"{self.base_url}/api/chat", payload)

        payload = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return await self._post(f"{self.base_url}/chat/completions", payload)

    def _parse(self, resp: httpx.Response) -> dict:
        if resp.status_code != 200:
            snippet = resp.text[:300]
            hint = ""
            if resp.status_code in ROTATE_ON_STATUS:
                hint = " - all configured API keys were rejected or rate-limited" if len(self.api_keys) > 1 else ""
            raise LLMError(f"LLM API error {resp.status_code}{hint}: {snippet}", status=resp.status_code)

        try:
            data = resp.json()
            if self.protocol == "ollama":
                message = _from_ollama_response(data)
            else:
                choice = data["choices"][0]["message"]
                message = {
                    "role": choice.get("role", "assistant"),
                    "content": choice.get("content"),
                    "tool_calls": choice.get("tool_calls"),
                }
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"unexpected LLM response shape: {resp.text[:300]}") from exc

        log.debug(
            "chat ok proto=%s keys=%d tool_calls=%s",
            self.protocol,
            len(self.api_keys),
            bool(message.get("tool_calls")),
        )
        return message

    async def health(self) -> dict:
        url = (
            f"{self.base_url}/api/tags"
            if self.protocol == "ollama"
            else f"{self.base_url}/models"
        )
        try:
            headers = self._auth_headers()
            async with httpx.AsyncClient(timeout=3.0, transport=self.transport) as client:
                resp = await client.get(url, headers=headers)
        except Exception as exc:
            return {"ok": False, "detail": f"unreachable: {type(exc).__name__}"}

        keys_note = f", {len(self.api_keys)} chave(s)" if self.api_keys else ""
        if resp.status_code == 200:
            return {"ok": True, "detail": f"{self.model} via {self.protocol} ({self.base_url}){keys_note}"}
        if resp.status_code in (401, 403):
            return {"ok": False, "detail": f"auth rejected ({resp.status_code}) - confira NOVA_LLM_API_KEY{keys_note}"}
        if resp.status_code == 429:
            return {"ok": False, "detail": f"rate limited (429){keys_note}"}
        return {"ok": True, "detail": f"endpoint respondeu {resp.status_code} (listagem não suportada)"}
