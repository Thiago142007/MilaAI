import json

from backend.app.plugins.loader import load_plugins
from backend.app.tools.base import ToolRegistry


def make_plugin(dir_path, name="hello"):
    plugin_dir = dir_path / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps({"name": name, "version": "1.0.0", "permissions": ["WEB"]}),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        """
from backend.app.tools.base import Tool, ok

async def handler():
    return ok(data="hello from plugin")

def register(registry, ctx=None):
    registry.register(Tool(
        name=f"plugin_{ctx.plugin_name}.hello",
        description="says hello",
        parameters={"properties": {}},
        handler=handler,
        permissions=ctx.plugin_permissions,
    ))
""",
        encoding="utf-8",
    )
    return plugin_dir


def test_plugin_loads_and_registers_tool(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    make_plugin(plugins_dir, "greeter")

    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == ["greeter"]
    tool = reg.get("plugin_greeter.hello")
    assert tool is not None
    assert tool.permissions == ["WEB"]


def test_broken_plugin_does_not_crash_loader(tmp_path):
    plugins_dir = tmp_path / "plugins"
    bad = make_plugin(plugins_dir, "broken")
    (bad / "plugin.py").write_text("raise RuntimeError('exploded')", encoding="utf-8")

    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == []


def test_incomplete_plugin_skipped(tmp_path):
    plugins_dir = tmp_path / "plugins"
    d = plugins_dir / "half"
    d.mkdir(parents=True)
    (d / "plugin.json").write_text("{}", encoding="utf-8")

    reg = ToolRegistry()
    loaded = load_plugins(reg, plugins_dir)
    assert loaded == []


async def test_plugin_tool_executes(tmp_path):
    plugins_dir = tmp_path / "plugins"
    make_plugin(plugins_dir, "exec")
    reg = ToolRegistry()
    load_plugins(reg, plugins_dir)
    result = await reg.get("plugin_exec.hello").handler()
    assert result["success"] and result["data"] == "hello from plugin"
