import json
import logging
import sys
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path


class RingBufferHandler(logging.Handler):
    def __init__(self, capacity: int = 1000) -> None:
        super().__init__()
        self.buffer: deque = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(
                {
                    "ts": record.created,
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
            )
        except Exception:
            pass


_ring = RingBufferHandler()


def get_ring() -> RingBufferHandler:
    return _ring


def setup_logging(level: str = "INFO", log_dir: str | Path = "logs") -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for h in list(root.handlers):
        root.removeHandler(h)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s :: %(message)s", "%H:%M:%S")
    )
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_path / "nova.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter(
            json.dumps(
                {
                    "ts": "%(created)f",
                    "level": "%(levelname)s",
                    "logger": "%(name)s",
                    "msg": "%(message)s",
                }
            )
            + "\n",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s|%(levelname)s|%(name)s|%(message)s")
    )
    root.addHandler(file_handler)
    root.addHandler(_ring)


class Timer:
    def __init__(self) -> None:
        self.start = time.perf_counter()

    def elapsed(self) -> float:
        return round(time.perf_counter() - self.start, 3)
