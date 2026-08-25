import logging
import os
import re
import threading
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import numpy as np

from .audio import apply_volume
from .cache import AudioCache
from .config import TTSConfig, get_tts_config
from .engine import BaseTTSEngine
from .preprocessor import TextPreprocessor

log = logging.getLogger("nova.voice.kokoro")


class KokoroEngine(BaseTTSEngine):
    """Local Kokoro-82M Text-to-Speech Engine using ONNX Runtime."""

    def __init__(self, config: Optional[TTSConfig] = None) -> None:
        self.config = config or get_tts_config()
        self.kokoro = None
        self.cache = AudioCache(max_size=self.config.cache_max_size, enabled=self.config.cache_enabled)
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        """Load Kokoro-82M ONNX model and voices into memory once."""
        if self._initialized and self.kokoro is not None:
            return

        with self._lock:
            if self._initialized and self.kokoro is not None:
                return

            model_path = str(self.config.model_path)
            voices_path = str(self.config.voices_path)

            if not os.path.exists(model_path) or not os.path.exists(voices_path):
                raise FileNotFoundError(
                    f"Kokoro model files missing: {model_path} or {voices_path}"
                )

            log.info("Initializing Kokoro-82M from %s (device: %s)", model_path, self.config.device)

            from kokoro_onnx import Kokoro
            self.kokoro = Kokoro(model_path, voices_path)
            self._initialized = True
            log.info("Kokoro-82M initialized successfully. Total voices: %d", len(self.get_available_voices()))

    def is_ready(self) -> bool:
        return self._initialized and self.kokoro is not None

    def get_available_voices(self) -> List[str]:
        if not self.is_ready():
            return ["pf_dora", "pm_alex", "af_heart", "af_bella", "af_sarah", "bf_emma"]
        return self.kokoro.get_voices()

    def _resolve_lang(self, voice: str, lang: Optional[str] = None) -> str:
        """Infer language code from voice prefix or explicit lang parameter."""
        if lang:
            return lang
        if voice.startswith("p"):
            return "pt-br"
        elif voice.startswith("a"):
            return "en-us"
        elif voice.startswith("b"):
            return "en-gb"
        elif voice.startswith("e"):
            return "es"
        elif voice.startswith("f"):
            return "fr"
        elif voice.startswith("h"):
            return "hi"
        elif voice.startswith("i"):
            return "it"
        elif voice.startswith("j"):
            return "ja"
        elif voice.startswith("z"):
            return "zh"
        return self.config.lang

    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        lang: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """Synthesize text into complete audio waveform."""
        self.initialize()

        cleaned = TextPreprocessor.clean_text(text)
        if not cleaned:
            return np.zeros(0, dtype=np.float32), self.config.sample_rate

        selected_voice = voice or self.config.voice
        selected_speed = speed if speed is not None else self.config.speed
        selected_lang = self._resolve_lang(selected_voice, lang)

        # Check Cache
        cached = self.cache.get(cleaned, selected_voice, selected_speed, selected_lang)
        if cached is not None:
            return cached

        with self._lock:
            samples, sample_rate = self.kokoro.create(
                cleaned,
                voice=selected_voice,
                speed=selected_speed,
                lang=selected_lang,
            )

        if self.config.volume != 1.0:
            samples = apply_volume(samples, self.config.volume)

        # Store in Cache
        self.cache.put(cleaned, selected_voice, selected_speed, selected_lang, samples, sample_rate)

        return samples, sample_rate

    def stream_generate(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        lang: Optional[str] = None,
    ) -> Generator[Tuple[np.ndarray, int], None, None]:
        """Yield audio chunk by chunk for progressive streaming."""
        self.initialize()

        cleaned = TextPreprocessor.clean_text(text)
        if not cleaned:
            return

        selected_voice = voice or self.config.voice
        selected_speed = speed if speed is not None else self.config.speed
        selected_lang = self._resolve_lang(selected_voice, lang)

        # Split text into natural sentence chunks
        sentences = re.split(r"(?<=[.!?;\n])\s+", cleaned)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            with self._lock:
                samples, sample_rate = self.kokoro.create(
                    sentence,
                    voice=selected_voice,
                    speed=selected_speed,
                    lang=selected_lang,
                )

            if self.config.volume != 1.0:
                samples = apply_volume(samples, self.config.volume)

            yield samples, sample_rate
