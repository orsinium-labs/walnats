from __future__ import annotations
from dataclasses import dataclass
from logging import getLogger

from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from ._actor import Actor
    from ._serializers import Model


M = TypeVar('M', bound=Model)
logger = getLogger(__package__)


@dataclass(frozen=True)
class ErrorContext(Generic[M]):
    actor: Actor
    message: M | None


class ErrorHandler(Protocol, Generic[M]):
    async def __call__(self, ctx: ErrorContext[M]) -> None:
        raise NotImplementedError


async def log_error(ctx: ErrorContext) -> None:
    msg = f'Unhandled exception in "{ctx.actor.name}" actor'
    logger.exception(msg)


async def do_nothing(ctx: ErrorContext) -> None:
    pass


async def explode(ctx: ErrorContext) -> None:
    raise


if TYPE_CHECKING:
    _: ErrorHandler
    _ = log_error
