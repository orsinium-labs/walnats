from __future__ import annotations

import gzip
import hmac
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Generic, TypeVar

from ._base import Serializer


if TYPE_CHECKING:
    from cryptography.fernet import Fernet as _Fernet


M = TypeVar('M')


@dataclass(frozen=True)
class GZipSerializer(Serializer[M], Generic[M]):
    """Compress serialized data using gzip compression algorithm.

    Args:
        serializer: serializer whose output should be compressed.
    """
    serializer: Serializer[M]
    level: int = 9

    def encode(self, message: M) -> bytes:
        data = self.serializer.encode(message)
        return gzip.compress(data, compresslevel=self.level)

    def decode(self, data: bytes) -> M:
        data = gzip.decompress(data)
        return self.serializer.decode(data)


@dataclass(frozen=True)
class FernetSerializer(Serializer[M], Generic[M]):
    """Sign and encrypt the message using Fernet algorithm.

    Args:
        serializer: serializer whose output should be encrypted.
        key: secret key to use. See ``cryptography`` docs on how to generate the key.

    Requires ``cryptography`` package to be installed.
    """
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


@dataclass(frozen=True)
class HMACSerializer(Serializer[M], Generic[M]):
    """Sign the message using HMAC algorithm.

    The signed binary digest will be added at the beginning of the message.

    Args:
        serializer: serializer whose output should be signed.
        key: the secret key to use.
        hash_algorithm: hash algorithm name to use, anything supported by ``hashlib``.
    """
    serializer: Serializer[M]
    key: bytes
    hash_algorithm: str = 'sha512'

    def encode(self, message: M) -> bytes:
        data = self.serializer.encode(message)
        digest = hmac.digest(key=self.key, msg=data, digest=self.hash_algorithm)
        return digest + data

    def decode(self, data: bytes) -> M:
        hasher = hmac.HMAC(key=self.key, digestmod=self.hash_algorithm)
        actual_digest = data[:hasher.digest_size]
        data = data[hasher.digest_size:]
        hasher.update(data)
        expected_digest = hasher.digest()
        if not hmac.compare_digest(actual_digest, expected_digest):
            raise ValueError('the message is corrupted or altered')
        return self.serializer.decode(data)
