from collections import OrderedDict
import hashlib
import threading
from typing import Optional, Tuple
import numpy as np


class AudioCache:
    """Thread-safe LRU cache for synthesized speech audio."""

    def __init__(self, max_size: int = 256, enabled: bool = True) -> None:
        self.max_size = max_size
        self.enabled = enabled
        self._cache: OrderedDict[str, Tuple[np.ndarray, int]] = OrderedDict()
        self._lock = threading.Lock()

    def _make_key(self, text: str, voice: str, speed: float, lang: str) -> str:
        content = f"{text.strip()}|{voice}|{speed:.2f}|{lang}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, text: str, voice: str, speed: float, lang: str) -> Optional[Tuple[np.ndarray, int]]:
        if not self.enabled:
            return None
        key = self._make_key(text, voice, speed, lang)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, text: str, voice: str, speed: float, lang: str, audio: np.ndarray, sample_rate: int) -> None:
        if not self.enabled or len(text.strip()) == 0:
            return
        key = self._make_key(text, voice, speed, lang)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                self._cache[key] = (audio.copy(), sample_rate)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
