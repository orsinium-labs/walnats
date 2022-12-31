from __future__ import annotations

import asyncio

import walnats


async def test_require__sync():
    connected = False
    log = []

    async def connect():
        nonlocal connected
        log.append('connecting')
        await asyncio.sleep(.001)
        connected = True
        log.append('connected')

    @walnats.decorators.require(lambda: connected)
    def handler(_: None) -> None:
        log.append('started')

    asyncio.create_task(connect())
    await handler(None)
    await handler(None)
    assert log == ['connecting', 'connected', 'started', 'started']


async def test_require__async():
    connected = False
    log = []

    async def connect():
        nonlocal connected
        log.append('connecting')
        await asyncio.sleep(.001)
        connected = True
        log.append('connected')

    @walnats.decorators.require(lambda: connected)
    async def handler(_: None) -> None:
        log.append('started')

    asyncio.create_task(connect())
    await handler(None)
    await handler(None)
    assert log == ['connecting', 'connected', 'started', 'started']
