from __future__ import annotations

import dataclasses
from typing import Generic, TypeVar

M = TypeVar('M')


@dataclasses.dataclass(frozen=True)
class Serializer(Generic[M]):
    model: type[M]

    @classmethod
    def new(cls, model: type[M]) -> Serializer[M] | None:
        raise NotImplementedError

    def encode(self, message: M) -> bytes:
        raise NotImplementedError

    def decode(self, data: bytes) -> M:
        raise NotImplementedError
