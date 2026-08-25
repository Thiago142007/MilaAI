import pytest
from backend.app.db.database import Database
from backend.app.memory.manager import MemoryManager
from backend.app.tools.base import ToolRegistry
from backend.app.tools.builtin.memory import register_tools


@pytest.mark.asyncio
async def test_procedural_memory(tmp_path):
    db = Database(tmp_path / "test_mem.db")
    mgr = MemoryManager(db)

    # Save procedure
    pid = mgr.save_procedure(
        name="open_discord",
        steps=["Find Discord window", "Focus window", "Read unread messages"],
        description="Opens and checks Discord",
    )
    assert pid > 0

    # Retrieve procedure
    proc = mgr.get_procedure("open_discord")
    assert proc is not None
    assert proc["name"] == "open_discord"
    assert len(proc["steps"]) == 3

    # List procedures
    procs = mgr.list_procedures()
    assert len(procs) >= 1

    # Tools
    reg = ToolRegistry()
    register_tools(reg, mgr)

    save_tool = reg.get("memory.save_procedure")
    get_tool = reg.get("memory.get_procedure")

    res_save = await save_tool.handler(
        name="build_project",
        steps=["Run pytest", "Build frontend", "Start server"],
    )
    assert res_save["success"] is True

    res_get = await get_tool.handler(name="build_project")
    assert res_get["success"] is True
    assert len(res_get["data"]["steps"]) == 3
