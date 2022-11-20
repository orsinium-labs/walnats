from __future__ import annotations

import dataclasses
from typing import Generic, TypeVar


T = TypeVar('T')


@dataclasses.dataclass(frozen=True)
class Serializer(Generic[T]):
    schema: type[T]

    @classmethod
    def new(cls, schema: type[T]) -> Serializer[T] | None:
        raise NotImplementedError

    def encode(self, message: T) -> bytes:
        raise NotImplementedError

    def decode(self, data: bytes) -> T:
        raise NotImplementedError
