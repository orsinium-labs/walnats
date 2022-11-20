from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Generic, TypeVar


if TYPE_CHECKING:
    import asyncio

    from nats.aio.msg import Msg

    from ._actor import Actor


M = TypeVar('M', bound=object)


@dataclass(frozen=True)
class Context(Generic[M]):
    actor: Actor
    message: M | None
    _msg: Msg

    @cached_property
    def metadata(self) -> Msg.Metadata:
        return self._msg.metadata

    @property
    def is_first_attempt(self) -> bool:
        """Check if this is the first attempt to handle the message.
        """
        return self.metadata.num_delivered == 0


@dataclass(frozen=True)
class ErrorContext(Context[M], Generic[M]):
    exception: Exception | asyncio.CancelledError


@dataclass(frozen=True)
class OkContext(Context[M], Generic[M]):
    duration: float
