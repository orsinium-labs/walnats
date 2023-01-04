from __future__ import annotations

import asyncio

import walnats

from ..helpers import duration_between


async def test_limit_not_reached__sync():
    log = []

    @walnats.decorators.rate_limit(10, 60)
    def handler(_: None) -> None:
        log.append('')

    tasks = [handler(None) for _ in range(10)]
    with duration_between(0, .1):
        await asyncio.gather(*tasks)
    assert len(log) == 10


async def test_limit_not_reached__async():
    log = []

    @walnats.decorators.rate_limit(10, 60)
    async def handler(_: None) -> None:
        log.append('')

    tasks = [handler(None) for _ in range(10)]
    with duration_between(0, .1):
        await asyncio.gather(*tasks)
    assert len(log) == 10


async def test_limit_reached__async():
    log = []

    @walnats.decorators.rate_limit(10, .1)
    async def handler(_: None) -> None:
        log.append('')

    tasks = [handler(None) for _ in range(10)]
    with duration_between(0, .1):
        await asyncio.gather(*tasks)
    with duration_between(.09, .11):
        await handler(None)
    assert len(log) == 11
