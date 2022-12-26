from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import walnats


@dataclass(frozen=True)
class Scheduler:
    conn: walnats.types.ConnectedEvents
    prefix: str = 'time'

    async def run(self, burst: bool = False) -> None:
        while True:
            await self._wait()
            now = datetime.now()
            coro = self._emit(now)
            asyncio.create_task(coro)
            if burst:
                return

    async def _wait(self) -> None:
        """Wait until the next minute +1s.
        """
        now = datetime.now()
        delay = 61 - now.second
        await asyncio.sleep(delay)

    async def _emit(self, now: datetime) -> None:
        parts = [f'{p:02}' for p in now.timetuple()[:5]]
        suffix = '.'.join(parts)
        await self.conn._nc.publish(f'{self.prefix}.{suffix}')
