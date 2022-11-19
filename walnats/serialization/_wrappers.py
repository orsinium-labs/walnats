from __future__ import annotations
from dataclasses import dataclass
import gzip as _gzip
from typing import Generic, TypeVar

from ._base import Serializer


M = TypeVar('M')


@dataclass(frozen=True)
class GZip(Serializer[M], Generic[M]):
    serializer: Serializer[M]
    level: int = 9

    def encode(self, message: M) -> bytes:
        data = self.serializer.encode(message)
        return _gzip.compress(data, compresslevel=self.level)

    def decode(self, data: bytes) -> M:
        data = _gzip.decompress(data)
        return self.serializer.decode(data)
