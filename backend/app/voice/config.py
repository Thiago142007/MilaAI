from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class TTSConfig:
    """Configuration for Local Kokoro-82M Text-to-Speech."""

    model_dir: Path = Path(__file__).resolve().parents[3] / "data" / "models" / "kokoro"
    model_path: Path = Path(__file__).resolve().parents[3] / "data" / "models" / "kokoro" / "kokoro-v1.0.onnx"
    voices_path: Path = Path(__file__).resolve().parents[3] / "data" / "models" / "kokoro" / "voices-v1.0.bin"

    voice: str = os.getenv("TTS_VOICE", "pf_dora")
    speed: float = float(os.getenv("TTS_SPEED", "1.0"))
    volume: float = float(os.getenv("TTS_VOLUME", "1.0"))
    device: str = os.getenv("TTS_DEVICE", "auto")
    sample_rate: int = 24000
    lang: str = os.getenv("TTS_LANG", "pt-br")
    cache_enabled: bool = os.getenv("TTS_CACHE_ENABLED", "true").lower() in ("1", "true", "yes")
    cache_max_size: int = int(os.getenv("TTS_CACHE_MAX_SIZE", "256"))

    def validate(self) -> None:
        """Validate paths and ranges."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        if not (0.2 <= self.speed <= 3.0):
            self.speed = 1.0
        if not (0.0 <= self.volume <= 2.0):
            self.volume = 1.0


_global_config: TTSConfig | None = None


def get_tts_config() -> TTSConfig:
    """Retrieve the global TTS configuration singleton."""
    global _global_config
    if _global_config is None:
        _global_config = TTSConfig()
        _global_config.validate()
    return _global_config
