from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Deque

from .models import LogEntry


class LogBuffer:
    def __init__(self, max_entries: int = 200) -> None:
        self._entries: Deque[LogEntry] = deque(maxlen=max_entries)

    def add(self, level: str, message: str) -> None:
        self._entries.append(
            LogEntry(timestamp=datetime.now(timezone.utc), level=level.upper(), message=message)
        )

    def as_list(self) -> list[dict[str, str]]:
        return [entry.to_dict() for entry in self._entries]

