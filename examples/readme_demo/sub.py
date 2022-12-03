import asyncio

import walnats

from .events import COUNT


async def run_subscriber() -> None:
    registry = walnats.Actors(
        walnats.Actor('print', COUNT, print),
    )
    async with registry.connect() as conn:
        await conn.register()
        await conn.listen()

asyncio.run(run_subscriber())
