import asyncio

import walnats

from .events import COUNT


async def run() -> None:
    events = walnats.Events(COUNT)
    async with events.connect() as conn:
        await conn.register()
        for i in range(1000):
            await conn.emit(COUNT, i)
            print(f'emitted {i}')
            await asyncio.sleep(1)

asyncio.run(run())
