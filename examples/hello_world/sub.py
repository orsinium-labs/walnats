
import asyncio

import walnats

from .events import COUNTER, CounterModel


async def print_counter(event: CounterModel) -> None:
    print(f'got value {event.value}')


async def run_subscriber() -> None:
    registry = walnats.Actors(
        walnats.Actor('print-counter', COUNTER, print_counter),
    )
    async with registry.connect() as conn:
        await conn.register()
        await conn.listen()


if __name__ == '__main__':
    asyncio.run(run_subscriber())
