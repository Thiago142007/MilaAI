import base64
import io
from typing import Tuple
import numpy as np
import soundfile as sf


def apply_volume(samples: np.ndarray, volume: float = 1.0) -> np.ndarray:
    """Adjust audio volume scaling and clamp to [-1.0, 1.0]."""
    if volume == 1.0:
        return samples
    scaled = samples * volume
    return np.clip(scaled, -1.0, 1.0)


def audio_to_wav_bytes(samples: np.ndarray, sample_rate: int = 24000, volume: float = 1.0) -> bytes:
    """Convert numpy float32 audio waveform to standard WAV byte buffer."""
    processed = apply_volume(samples, volume)
    buffer = io.BytesIO()
    sf.write(buffer, processed, sample_rate, format="WAV", subtype="PCM_16")
    buffer.seek(0)
    return buffer.read()


def audio_to_base64_data_uri(samples: np.ndarray, sample_rate: int = 24000, volume: float = 1.0) -> str:
    """Encode audio into standard base64 data URI (data:audio/wav;base64,...)."""
    wav_bytes = audio_to_wav_bytes(samples, sample_rate, volume)
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    return f"data:audio/wav;base64,{b64}"
