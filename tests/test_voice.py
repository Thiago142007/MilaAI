import pytest
from backend.app.tools.base import ToolRegistry
from backend.app.tools.builtin.voice import register_tools
from backend.app.voice.manager import VoiceManager


@pytest.mark.asyncio
async def test_voice_manager_status(tmp_path):
    mgr = VoiceManager(tmp_path)
    st = mgr.status()
    assert st["ok"] is True
    assert "detail" in st


@pytest.mark.asyncio
async def test_voice_tools(tmp_path):
    mgr = VoiceManager(tmp_path)
    reg = ToolRegistry()
    register_tools(reg, mgr)

    assert reg.get("voice.speak") is not None
    assert reg.get("voice.status") is not None

    status_tool = reg.get("voice.status")
    res = await status_tool.handler()
    assert res["success"] is True
    assert res["data"]["ok"] is True


@pytest.mark.asyncio
async def test_voice_transcribe(tmp_path):
    mgr = VoiceManager(tmp_path)
    text = await mgr.transcribe(b"dummy_audio_bytes", audio_format="wav")
    assert isinstance(text, str)
