import asyncio
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .audio import audio_to_base64_data_uri, audio_to_wav_bytes
from .config import TTSConfig, get_tts_config
from .kokoro_engine import KokoroEngine
from .queue import AudioPlaybackQueue

log = logging.getLogger("nova.voice")


class VoiceManager:
    """Unified Voice Manager for NOVA powered exclusively by local Kokoro-82M."""

    def __init__(self, config: Optional[TTSConfig] = None) -> None:
        self.config = config or get_tts_config()
        self.engine = KokoroEngine(self.config)
        self.queue = AudioPlaybackQueue()
        self.enabled = True

        # Preload model in background thread on startup
        threading.Thread(target=self._preload, daemon=True).start()

    def _preload(self) -> None:
        try:
            self.engine.initialize()
        except Exception as e:
            log.warning("Background Kokoro initialization error: %s", e)

    def status(self) -> Dict[str, Any]:
        """Check voice subsystem readiness and Kokoro-82M engine status."""
        is_ready = self.engine.is_ready()
        return {
            "ok": True,
            "tts_ready": is_ready,
            "engine": "Kokoro-82M",
            "device": self.config.device,
            "default_voice": self.config.voice,
            "speed": self.config.speed,
            "volume": self.config.volume,
            "sample_rate": self.config.sample_rate,
            "available_voices": self.get_voices(),
            "detail": "Kokoro-82M 100% Local TTS Engine Ready",
        }

    def get_voices(self) -> List[str]:
        """List all available voices from the Kokoro model."""
        return self.engine.get_available_voices()

    def update_config(
        self,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        volume: Optional[float] = None,
        device: Optional[str] = None,
    ) -> None:
        """Update runtime TTS configuration dynamically."""
        if voice:
            self.config.voice = voice
        if speed is not None:
            self.config.speed = max(0.2, min(3.0, speed))
        if volume is not None:
            self.config.volume = max(0.0, min(2.0, volume))
        if device:
            self.config.device = device

    async def generate_audio_base64(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> str:
        """Synthesize text and return base64 WAV data URI."""
        if not text.strip():
            return ""

        def _sync_gen():
            samples, sample_rate = self.engine.generate(
                text=text,
                voice=voice or self.config.voice,
                speed=speed or self.config.speed,
            )
            return audio_to_base64_data_uri(samples, sample_rate, self.config.volume)

        return await asyncio.to_thread(_sync_gen)

    async def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        wait: bool = False,
    ) -> bool:
        """Speak text aloud using local audio output asynchronously."""
        if not text.strip() or not self.enabled:
            return False

        async def _play_task():
            def _sync_synthesize():
                return self.engine.generate(
                    text=text,
                    voice=voice or self.config.voice,
                    speed=speed or self.config.speed,
                )

            samples, sample_rate = await asyncio.to_thread(_sync_synthesize)
            wav_bytes = audio_to_wav_bytes(samples, sample_rate, self.config.volume)

            # Local playback via winsound (Windows)
            def _sync_play():
                try:
                    import winsound
                    winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                except Exception as e:
                    log.debug("Local winsound playback: %s", e)

            await asyncio.to_thread(_sync_play)

        if wait:
            await self.queue.play_or_enqueue(_play_task)
            return True
        else:
            asyncio.create_task(self.queue.play_or_enqueue(_play_task))
            return True

    def stop_speaking(self) -> None:
        """Interrupt any ongoing TTS playback and clear the queue."""
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        self.queue.stop()

    def is_speaking(self) -> bool:
        """Check if speech audio is currently playing."""
        return self.queue.is_playing


_global_voice_manager: Optional[VoiceManager] = None


def get_voice_manager() -> VoiceManager:
    """Retrieve the global VoiceManager singleton."""
    global _global_voice_manager
    if _global_voice_manager is None:
        _global_voice_manager = VoiceManager()
    return _global_voice_manager
