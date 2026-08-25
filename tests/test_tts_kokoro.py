import asyncio
import os
import pytest
import numpy as np
from pathlib import Path

from backend.app.voice.config import TTSConfig, get_tts_config
from backend.app.voice.kokoro_engine import KokoroEngine
from backend.app.voice.preprocessor import TextPreprocessor
from backend.app.voice.cache import AudioCache
from backend.app.voice.queue import AudioPlaybackQueue
from backend.app.voice.manager import VoiceManager
from backend.app.voice.audio import audio_to_wav_bytes, audio_to_base64_data_uri


@pytest.fixture(scope="module")
def tts_engine():
    config = get_tts_config()
    engine = KokoroEngine(config)
    engine.initialize()
    return engine


def test_model_initialization(tts_engine):
    """Test that model initializes once and is ready in memory."""
    assert tts_engine.is_ready() is True
    voices = tts_engine.get_available_voices()
    assert len(voices) > 0
    assert "pf_dora" in voices
    assert "pm_alex" in voices


def test_text_preprocessor():
    """Test text cleaning for Markdown, code blocks, and URLs."""
    raw = "Instale o pacote `numpy` usando ```pip install numpy```. Acesse [Google](https://google.com) **agora**!!!"
    cleaned = TextPreprocessor.clean_text(raw)
    assert "```" not in cleaned
    assert "`" not in cleaned
    assert "https://" not in cleaned
    assert "Google" in cleaned
    assert "agora" in cleaned


def test_synthesis_short_phrase_ptbr(tts_engine):
    """Test short Portuguese phrase with pf_dora."""
    text = "Olá! Tudo bem com você?"
    samples, sr = tts_engine.generate(text, voice="pf_dora", speed=1.0)
    assert isinstance(samples, np.ndarray)
    assert len(samples) > 0
    assert sr == 24000


def test_synthesis_long_phrase_with_numbers(tts_engine):
    """Test synthesis of long phrase with numbers and punctuation."""
    text = "O sistema foi atualizado no dia 25 de agosto de 2026 com 100% de sucesso e taxa de 50.5%."
    samples, sr = tts_engine.generate(text, voice="pf_dora", speed=1.0)
    assert len(samples) > 1000
    assert sr == 24000


def test_audio_cache(tts_engine):
    """Test that subsequent identical calls utilize cache."""
    text = "Frase para teste de cache local."
    # 1st call - generate and put in cache
    s1, sr1 = tts_engine.generate(text, voice="pf_dora", speed=1.0)
    # 2nd call - retrieve from cache
    s2, sr2 = tts_engine.generate(text, voice="pf_dora", speed=1.0)
    assert np.array_equal(s1, s2)
    assert sr1 == sr2


def test_audio_encoding(tts_engine):
    """Test WAV and Base64 conversion."""
    samples, sr = tts_engine.generate("Teste de áudio.", voice="pf_dora")
    wav_bytes = audio_to_wav_bytes(samples, sr)
    assert wav_bytes.startswith(b"RIFF")
    b64_uri = audio_to_base64_data_uri(samples, sr)
    assert b64_uri.startswith("data:audio/wav;base64,")


@pytest.mark.asyncio
async def test_playback_queue_and_interruption():
    """Test playback queue execution and immediate cancellation."""
    queue = AudioPlaybackQueue()
    executed = []

    async def dummy_play():
        executed.append("start")
        await asyncio.sleep(0.5)
        executed.append("end")

    # Start play
    task = asyncio.create_task(queue.play_or_enqueue(dummy_play))
    await asyncio.sleep(0.05)
    assert queue.is_playing is True

    # Interrupt
    queue.stop()
    await asyncio.sleep(0.05)
    assert queue.is_playing is False
    assert "start" in executed
    assert "end" not in executed


@pytest.mark.asyncio
async def test_voice_manager_status_and_b64():
    """Test VoiceManager integration."""
    vm = VoiceManager()
    status = vm.status()
    assert status["ok"] is True
    assert status["engine"] == "Kokoro-82M"
    assert "pf_dora" in status["available_voices"]

    b64 = await vm.generate_audio_base64("Mila está pronta.", voice="pf_dora")
    assert b64.startswith("data:audio/wav;base64,")
