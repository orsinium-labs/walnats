from __future__ import annotations

import dataclasses
from typing import Generic, TypeVar


T = TypeVar('T')


@dataclasses.dataclass(frozen=True)
class Serializer(Generic[T]):
    """Base class for all serializers.

    Serializers convert Python message into binary payload,
    so that it can be transferred over the network.
    """
    schema: type[T]

    @classmethod
    def new(cls, schema: type[T]) -> Serializer[T] | None:
        """Create a new instance of the middleware for the given type if possible.

        This constructor is used by ``get_serializer`` to pick a serializer
        when you don't specify one for an :class:`walnats.Event`.
        You don't need to implement it for your custom serializers because you
        specify them explicitly.
        """
        raise NotImplementedError

    def encode(self, message: T) -> bytes:
        """Convert a Python message into binary Nats message payload.
        """
        raise NotImplementedError

    def decode(self, data: bytes) -> T:
        """Convert a binary Nats message payload into Python message.
        """
        raise NotImplementedError
