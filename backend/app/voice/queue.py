import asyncio
import logging
from typing import Callable, Optional

log = logging.getLogger("nova.voice.queue")


class AudioPlaybackQueue:
    """Manages sequential audio playback tasks, ensuring no overlapping speech."""

    def __init__(self) -> None:
        self._current_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._is_playing = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    async def play_or_enqueue(self, play_fn: Callable[[], asyncio.Future]) -> None:
        """Enqueue and execute a playback function sequentially."""
        # Cancel previous if still active
        self.stop()
        self._stop_event.clear()
        self._is_playing = True

        async def _runner():
            try:
                await play_fn()
            except asyncio.CancelledError:
                log.debug("Speech playback cancelled")
            except Exception as e:
                log.error("Error during speech playback: %s", e)
            finally:
                self._is_playing = False

        self._current_task = asyncio.create_task(_runner())
        await self._current_task

    def stop(self) -> None:
        """Instantly interrupt any ongoing playback."""
        self._stop_event.set()
        self._is_playing = False
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self._current_task = None
