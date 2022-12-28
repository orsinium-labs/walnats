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
    """Emit periodic events.

    By default, emits "minute-passed" event every 60 seconds.
    Use it for running scheduled and periodic tasks.

    ::

        clock = walnats.Clock()
        events = walnats.Events(clock.event)
        async with events as conn:
            await conn.register()
            await clock.run()

    The interval can be adjusted either by setting a custom ``duration``
    or by using :func:`walnats.decorators.filter_time`.

    ::

        clock_5m = walnats.Clock(
            event=walnats.Event('5m-passed', datetime),
            duration=5 * 60,
        )

    Args:
        event: the event to be emitted on each tick.
        meta: headers to be included into the message,
            same as ``meta`` argument of :meth:`walnats.types.ConnectedEvents.emit`.
        period: how often (in seconds) events should be emitted.
            The actual delta between event can fluctuate depending on when the async task
            gets woke up by the scheduler and how long it takes to publish the event.
            If, for some reason, the event can't be emitted before the time comes to emit
            the next one, it won't be emitted.
        now: callback that returns the current time. Useful for testing or black magic.

    It is safe to run multiple clocks on the same nats instance,
    events will not be duplicated. It might be a good idea to run a separate clock
    on each nats cluster, so that in case of netwrok failure between clusters
    events will still be coming in each of them.
    """
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
        """Run the clock, start emitting events in an infinite loop.

        Args:
            conn: connected events instance.
            burst: if True, emit one event in the right time and exit.
                Useful for testing.
        """
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
        """Wait until the next minute +ε.
        """
        now = self.now().timestamp()
        delay = self.period - (now % self.period) + .001
        await asyncio.sleep(delay)

    async def _emit(
        self,
        conn: walnats.types.ConnectedEvents,
        now: datetime,
    ) -> None:
        uid = now.timestamp() % self.period
        await conn.emit(self.event, now, uid=f'{uid}', meta=self.meta)
