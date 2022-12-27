from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import Awaitable, Callable, Iterable


DTHandler = Callable[[datetime], 'None | Awaitable[None]']


@dataclass
class filter_time:
    year: int | Iterable[int] | None = None
    month: int | Iterable[int] | None = None
    day: int | Iterable[int] | None = None
    hour: int | Iterable[int] | None = None
    minute: int | Iterable[int] | None = None

    def __call__(self, handler: DTHandler) -> DTHandler:

        def wrapper(dt: datetime) -> None | Awaitable[None]:
            for pattern, value in zip(self._patterns, dt.timetuple()):
                if pattern and value not in pattern:
                    return None
            return handler(dt)

        return wrapper

    @cached_property
    def _patterns(self) -> list[frozenset[int]]:
        parts: list[frozenset[int]] = []
        for part in (self.year, self.month, self.day, self.hour, self.minute):
            if isinstance(part, int):
                assert part < 60 or part > 2021
                subparts = frozenset({part})
            elif part is None:
                subparts = frozenset()
            else:
                subparts = frozenset(part)
            parts.append(subparts)
        return parts
