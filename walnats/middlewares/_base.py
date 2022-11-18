from __future__ import annotations
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from .._context import Context, ErrorContext, OkContext


M = TypeVar('M')


class BaseMiddleware(Generic[M]):
    __slots__ = ()

    async def on_start(self, ctx: Context[M]) -> None:
        pass

    async def on_failure(self, ctx: ErrorContext[M]) -> None:
        pass

    async def on_success(self, ctx: OkContext[M]) -> None:
        pass
