from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import cached_property, wraps
from typing import Awaitable, Callable, Iterable


@dataclass(frozen=True)
class filter_time:
    """Run the handler only if the input time matches the pattern.

    The decorator is a companion for :class:`walnats.Clock`
    in situations when an actor doesn't need to run every minute
    but you don't have enough actors to create a separate clock just for them.

    The idea is similar to how cron patterns work. The arguments form the pattern
    to match. If an argument is not specified, any value is accepted.
    If one or multiple values specified, any of the given values should match.

    Run the handler once a day at midnight::

        @walnats.decorators.filter_time(hour=0, minute=0)
        async def create_backup(dt):
            ...

    Run the handler every 5 minutes::

        @walnats.decorators.filter_time(minute=range(0, 60, 5))
        async def send_pulse(dt):
            ...

    """
    year: int | Iterable[int] | None = None
    month: int | Iterable[int] | None = None
    day: int | Iterable[int] | None = None
    hour: int | Iterable[int] | None = None
    minute: int | Iterable[int] | None = None

    def __call__(
        self,
        handler: Callable[[datetime], None | Awaitable[None]],
    ) -> Callable[[datetime], None | Awaitable[None]]:

        @wraps(handler)
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
