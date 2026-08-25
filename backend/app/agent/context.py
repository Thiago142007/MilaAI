import json
import logging

from backend.app.agent.prompts import build_system_prompt
from backend.app.memory.manager import MemoryManager

log = logging.getLogger("nova.context")


class ContextBuilder:
    def __init__(self, memory: MemoryManager, mode: str, workspace: str) -> None:
        self.memory = memory
        self.mode = mode
        self.workspace = workspace

    def build(
        self,
        conversation_id: str,
        runtime_notes: list[str] | None = None,
        task_description: str | None = None,
    ) -> list[dict]:
        messages: list[dict] = [
            {
                "role": "system",
                "content": build_system_prompt(self.mode, self.workspace),
            }
        ]

        relevant = []
        if task_description:
            relevant = self.memory.recall(task_description, k=3)
        elif messages:
            pass
        if relevant:
            mem_lines = "\n".join(f"- {m['content']}" for m in relevant)
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant long-term memories:\n{mem_lines}",
                }
            )

        history = self.memory.get_messages(conversation_id)
        for row in history:
            role = row["role"]
            content = row["content"]
            if role == "assistant":
                envelope = _parse_envelope(content)
                msg = {"role": "assistant", "content": envelope.get("content")}
                if envelope.get("tool_calls"):
                    msg["tool_calls"] = envelope["tool_calls"]
                messages.append(msg)
            elif role == "tool":
                env = _parse_envelope(content)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": env.get("tool_call_id", ""),
                        "content": env.get("content", ""),
                    }
                )
            else:
                messages.append({"role": role, "content": content})

        if runtime_notes:
            notes = "\n".join(f"- {n}" for n in runtime_notes[-5:])
            messages.append(
                {
                    "role": "system",
                    "content": f"RUNTIME NOTES (pay attention):\n{notes}",
                }
            )
        return messages


def _parse_envelope(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {"content": raw}


def make_assistant_envelope(content, tool_calls=None) -> str:
    return json.dumps(
        {
            "content": content,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"].get("arguments", "{}"),
                    },
                }
                for tc in (tool_calls or [])
            ],
        },
        ensure_ascii=False,
    )


def make_tool_envelope(tool_call_id: str, content: str) -> str:
    return json.dumps({"tool_call_id": tool_call_id, "content": content}, ensure_ascii=False)
