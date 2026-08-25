from backend.app.tools.base import Tool, ok


async def handler() -> dict:
    return ok(data={"hello": "world", "plugin": True})


def register(registry, ctx=None):
    registry.register(
        Tool(
            name="plugin_example.hello",
            description="Example plugin tool - returns a hello payload.",
            parameters={"properties": {}},
            handler=handler,
            permissions=[],
            risk="low",
            category="plugin",
        )
    )
