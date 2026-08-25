import pytest

from backend.app.tools.base import ToolRegistry, fail, ok
from backend.app.tools.builtin import filesystem


@pytest.fixture
def fs_env(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    ctx = filesystem.FsContext(workspace)
    reg = ToolRegistry()
    filesystem.register_tools(reg, ctx)
    return ctx, reg


async def test_write_read_list(fs_env):
    ctx, reg = fs_env
    r = await reg.get("fs.write").handler(path="a/b.txt", content="hello")
    assert r["success"]
    assert (ctx.workspace_root / "a" / "b.txt").read_text(encoding="utf-8") == "hello"

    r = await reg.get("fs.read").handler(path="a/b.txt")
    assert r["success"] and r["data"]["content"] == "hello"

    r = await reg.get("fs.list").handler(path=".")
    names = [e["name"] for e in r["data"]["entries"]]
    assert "a" in names


async def test_read_rejects_binary(fs_env):
    ctx, reg = fs_env
    (ctx.workspace_root / "bin.dat").write_bytes(b"\x00\x01\x02binary")
    r = await reg.get("fs.read").handler(path="bin.dat")
    assert not r["success"] and "binary" in r["error"]


async def test_write_refuses_env_files(fs_env):
    _, reg = fs_env
    r = await reg.get("fs.write").handler(path=".env", content="SECRET=1")
    assert not r["success"]
    assert not r["recoverable"]


async def test_move_copy_search_delete(fs_env):
    ctx, reg = fs_env
    await reg.get("fs.write").handler(path="x.txt", content="123")

    r = await reg.get("fs.copy").handler(src="x.txt", dst="y.txt")
    assert r["success"]

    r = await reg.get("fs.move").handler(src="y.txt", dst="sub/y.txt")
    assert r["success"]
    assert (ctx.workspace_root / "sub" / "y.txt").exists()

    r = await reg.get("fs.search").handler(pattern="*.txt", path=".")
    paths = [m["path"] for m in r["data"]["matches"]]
    assert any("x.txt" in p for p in paths) and any("y.txt" in p for p in paths)

    r = await reg.get("fs.delete").handler(path="sub")
    assert r["success"] and r["data"]["items_removed"] == 1


async def test_missing_paths_fail_gracefully(fs_env):
    _, reg = fs_env
    r = await reg.get("fs.read").handler(path="ghost.txt")
    assert not r["success"] and r["recoverable"]
