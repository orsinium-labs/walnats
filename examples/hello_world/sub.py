
import asyncio

import walnats

from .events import COUNTER_EVENT, CounterModel


async def print_counter(event: CounterModel) -> None:
    print(f'got value {event.value}')


async def run_subscriber() -> None:
    await walnats.run_actors(
        walnats.Actor('print_counter', COUNTER_EVENT, print_counter),
    )


if __name__ == '__main__':
    asyncio.run(run_subscriber())
