from __future__ import annotations

from typing import TypeVar

from . import _serializers as ss
from ._base import Serializer


SERIALIZERS: tuple[type[Serializer], ...] = (
    ss.PydanticSerializer,
    ss.ProtobufSerializer,
    ss.DataclassSerializer,
    ss.BytesSerializer,
    ss.DatetimeSerializer,
    ss.PrimitiveSerializer,
    ss.MarshmallowSerializer,
)

T = TypeVar('T')


def get_serializer(schema: type[T]) -> Serializer[T]:
    for serializer_class in SERIALIZERS:
        serializer = serializer_class.new(schema)
        if serializer is not None:
            return serializer
    raise RuntimeError(f'cannot find serializer for {schema.__name__}')
