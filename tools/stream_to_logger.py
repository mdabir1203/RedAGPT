"""Utilities for piping stdout into the logging framework."""

from __future__ import annotations

import logging
from typing import Iterable


class StreamToLogger:
    """File-like object redirecting writes to a :mod:`logging` logger."""

    def __init__(self, logger: logging.Logger, log_level: int = logging.INFO) -> None:
        self.logger = logger
        self.log_level = log_level

    def write(self, buf: str) -> None:  # pragma: no cover - simple delegation
        lines: Iterable[str] = buf.rstrip().splitlines()
        for line in lines:
            self.logger.log(self.log_level, line.rstrip())

    def flush(self) -> None:
        """Maintain the file-like interface expected by :class:`io.TextIOBase`."""
        # No-op: logging handlers manage their own flushing.
        return
