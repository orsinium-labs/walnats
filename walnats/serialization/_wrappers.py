from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
import gzip
from typing import TYPE_CHECKING, Generic, TypeVar

from ._base import Serializer

if TYPE_CHECKING:
    from cryptography.fernet import Fernet as _Fernet


M = TypeVar('M')


@dataclass(frozen=True)
class GZip(Serializer[M], Generic[M]):
    serializer: Serializer[M]
    level: int = 9

    def encode(self, message: M) -> bytes:
        data = self.serializer.encode(message)
        return gzip.compress(data, compresslevel=self.level)

    def decode(self, data: bytes) -> M:
        data = gzip.decompress(data)
        return self.serializer.decode(data)


@dataclass(frozen=True)
class Fernet(Serializer[M], Generic[M]):
    serializer: Serializer[M]
    key: str | bytes

    @cached_property
    def _fernet(self) -> _Fernet:
        from cryptography.fernet import Fernet as _Fernet
        return _Fernet(key=self.key)

    def encode(self, message: M) -> bytes:
        data = self.serializer.encode(message)
        return self._fernet.encrypt(data)

    def decode(self, data: bytes) -> M:
        data = self._fernet.decrypt(data)
        return self.serializer.decode(data)
