from __future__ import annotations

import asyncio
import dataclasses
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from .._tasks import Tasks
from ._event import Event


if TYPE_CHECKING:
    import walnats


@dataclasses.dataclass(frozen=True)
class Clock:
    event: Event[datetime] = dataclasses.field(
        default_factory=lambda: Event('minute-passed', datetime),
    )
    meta: dict[str, str] | None = None
    period: int = 60
    now: Callable[[], datetime] = datetime.now

    async def run(
        self,
        conn: walnats.types.ConnectedEvents,
        burst: bool = False,
    ) -> None:
        tasks = Tasks(f'clock/{self.event.name}')
        try:
            while True:
                await self._wait()
                now = datetime.now()
                coro = self._emit(conn, now)
                tasks.start(coro, f'clock/{self.event}/tick/{now.minute}')
                if burst:
                    await tasks.wait()
                    return
        finally:
            tasks.cancel()

    async def _wait(self) -> None:
        """Wait until the next minute +1s.
        """
        now = self.now().timestamp()
        delay = self.period - (now % self.period) + 1
        await asyncio.sleep(delay)

    async def _emit(
        self,
        conn: walnats.types.ConnectedEvents,
        now: datetime,
    ) -> None:
        uid = now.timestamp() % self.period
        await conn.emit(self.event, now, uid=f'{uid}', meta=self.meta)
