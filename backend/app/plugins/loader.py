import importlib.util
import json
import logging
from pathlib import Path

log = logging.getLogger("nova.plugins")

MANIFEST_NAME = "plugin.json"


class PluginError(Exception):
    pass


def load_plugins(registry, plugins_dir: Path) -> list[str]:
    if not plugins_dir.exists():
        return []
    loaded = []
    for plugin_dir in sorted(p for p in plugins_dir.iterdir() if p.is_dir()):
        manifest_path = plugin_dir / MANIFEST_NAME
        entry_path = plugin_dir / "plugin.py"
        if not manifest_path.exists() or not entry_path.exists():
            log.debug("skipping %s (missing %s or plugin.py)", plugin_dir.name, MANIFEST_NAME)
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            name = manifest.get("name", plugin_dir.name)
            version = manifest.get("version", "0.0.0")
            permissions = manifest.get("permissions", [])

            spec = importlib.util.spec_from_file_location(
                f"nova_plugin_{plugin_dir.name}", entry_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            register = getattr(module, "register", None)
            if not callable(register):
                raise PluginError("plugin.py must define register(registry, ctx=None)")

            class Ctx:
                pass

            ctx = Ctx()
            ctx.plugin_name = name
            ctx.plugin_permissions = permissions

            before = {t.name for t in registry.all()}
            register(registry, ctx)
            added = [t.name for t in registry.all() if t.name not in before]

            log.info(
                "plugin loaded: %s v%s (tools: %s, permissions: %s)",
                name,
                version,
                added or "-",
                permissions or "-",
            )
            loaded.append(name)
        except Exception as exc:
            log.error("plugin %s failed to load: %s", plugin_dir.name, exc)
    return loaded
