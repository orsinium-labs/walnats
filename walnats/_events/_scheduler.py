from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .._constants import HEADER_ID
from .._tasks import Tasks


if TYPE_CHECKING:
    import walnats


@dataclass(frozen=True)
class Scheduler:
    prefix: str = 'time'
    headers: dict[str, str] | None = None

    async def run(
        self,
        conn: walnats.types.ConnectedEvents,
        burst: bool = False,
    ) -> None:
        tasks = Tasks('scheduler')
        try:
            while True:
                await self._wait()
                now = datetime.now()
                coro = self._emit(conn, now)
                tasks.start(coro, f'scheduler/tick/{now.minute}')
                if burst:
                    await tasks.wait()
                    return
        finally:
            tasks.cancel()

    async def _wait(self) -> None:
        """Wait until the next minute +1s.
        """
        now = datetime.now()
        delay = 61 - now.second
        await asyncio.sleep(delay)

    async def _emit(
        self,
        conn: walnats.types.ConnectedEvents,
        now: datetime,
    ) -> None:
        parts = [f'{p:02}' for p in now.timetuple()[:5]]
        suffix = '.'.join(parts)
        headers = {HEADER_ID: suffix}
        if self.headers is not None:
            headers.update(self.headers)
        await conn._nc.publish(f'{self.prefix}.{suffix}')
