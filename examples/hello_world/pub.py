
import asyncio
from itertools import count

import walnats

from .events import COUNTER_EVENT, CounterModel


async def run_publisher() -> None:
    events = walnats.Events(
        COUNTER_EVENT,
    )
    conn = await events.connect(["nats://localhost:4222"])
    await conn.register_events()
    for i in count():
        event = CounterModel(value=i)
        await conn.emit(COUNTER_EVENT, event)
        print(f'sent value {event.value}')
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(run_publisher())
