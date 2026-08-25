from abc import ABC, abstractmethod
from typing import Generator, Optional, Tuple
import numpy as np


class BaseTTSEngine(ABC):
    """Abstract Base Class for Text-to-Speech engines."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the model and resources."""
        pass

    @abstractmethod
    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        lang: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """Generate full audio waveform and sample rate for a given text."""
        pass

    @abstractmethod
    def stream_generate(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        lang: Optional[str] = None,
    ) -> Generator[Tuple[np.ndarray, int], None, None]:
        """Yield audio chunks incrementally as sentences are synthesized."""
        pass

    @abstractmethod
    def get_available_voices(self) -> list[str]:
        """List all available voice identifiers."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if model is loaded in memory and ready."""
        pass
