from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import cached_property, wraps
from typing import Awaitable, Callable, TypeVar


DEFAULT_LOGGER = logging.getLogger(__package__)
E = TypeVar('E')


@dataclass(frozen=True)
class rate_limit:
    """Limit how many jobs at most can be started per time interval.

    The count starts as soon as the handler starts. For example, if you limit 10 jobs
    per 60 seconds, 11th job will wait while 60 seconds pass since the first jobs
    has been started before starting itself.

    ::

        @walnats.decorators.rate_limit(32, 60)
        async def send_sms(phone_number: int) -> None:
            ...

    Args:
        max_jobs: the jobs limit in the time interval.
        period: the time interval (in seconds).
    """
    max_jobs: int
    period: float

    def __call__(
        self,
        handler: Callable[[E], None | Awaitable[None]],
    ) -> Callable[[E], Awaitable[None]]:
        assert self.max_jobs >= 1
        assert self.period > 0

        @wraps(handler)
        async def wrapper(event: E) -> None:
            await self._semaphore.acquire()
            asyncio.create_task(self._release())
            result = handler(event)
            if result is not None:
                await result
        return wrapper

    @cached_property
    def _semaphore(self) -> asyncio.Semaphore:
        return asyncio.BoundedSemaphore(self.max_jobs)

    async def _release(self) -> None:
        await asyncio.sleep(self.period)
        self._semaphore.release()
