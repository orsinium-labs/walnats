
import asyncio
import walnats
from .events import COUNTER_EVENT, CounterModel


async def print_counter(event: CounterModel) -> None:
    print(f'got value {event.value}')


ACTORS = walnats.Actors(
    walnats.Actor('print_counter', COUNTER_EVENT, print_counter)
)


async def run_subscriber() -> None:
    conn = await ACTORS.connect(["nats://localhost:4222"])
    await conn.register_actors()
    await conn.listen()


if __name__ == '__main__':
    asyncio.run(run_subscriber())
