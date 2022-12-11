from __future__ import annotations

from dataclasses import dataclass

from ._base import Serializer


try:
    import msgpack
except ImportError:
    msgpack = None


@dataclass(frozen=True)
class MessagePackSerializer(Serializer[object]):
    """Serialize built-in types as msgpack message.

    Requires ``msgpack`` package to be installed.
    """
    schema: type[object] = object

    def encode(self, message: object) -> bytes:
        return msgpack.packb(message)

    def decode(self, data: bytes) -> object:
        return msgpack.unpackb(data)
