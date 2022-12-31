from __future__ import annotations

import asyncio
from typing import Awaitable

import pytest

import walnats


def test_suppress__sync():
    @walnats.decorators.suppress(TypeError)
    def handler(exc: Exception | type[Exception] | None) -> None:
        if exc:
            raise exc

    with pytest.raises(ValueError):
        handler(ValueError('hi'))
    with pytest.raises(ValueError):
        handler(ValueError)
    handler(TypeError('hello'))
    handler(TypeError)
    handler(None)


async def test_suppress__async():
    @walnats.decorators.suppress(TypeError)
    async def handler(exc: Exception | type[Exception] | None) -> None:
        if exc:
            raise exc

    with pytest.raises(ValueError):
        await handler(ValueError('hi'))
    with pytest.raises(ValueError):
        await handler(ValueError)
    await handler(TypeError('hello'))
    await handler(TypeError)
    await handler(None)


async def test_suppress__sync_async():
    async def inner(exc: Exception | type[Exception] | None) -> None:
        await asyncio.sleep(0)
        if exc:
            raise exc

    @walnats.decorators.suppress(TypeError)
    def handler(exc: Exception | type[Exception] | None) -> Awaitable[None]:
        return inner(exc)

    with pytest.raises(ValueError):
        await handler(ValueError('hi'))
    with pytest.raises(ValueError):
        await handler(ValueError)
    await handler(TypeError('hello'))
    await handler(TypeError)
    await handler(None)
