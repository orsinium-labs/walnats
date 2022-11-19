from typing import TypeVar
from ._base import Serializer

from . import _serializers as ss

SERIALIZERS: tuple[type[Serializer], ...] = (
    ss.PydanticSerializer,
    ss.DataclassSerializer,
    ss.BytesSerializer,
    ss.DatetimeSerializer,
    ss.PrimitiveSerializer,
)

M = TypeVar('M')


def get_serializer(model: type[M]) -> Serializer[M]:
    for serializer_class in SERIALIZERS:
        serializer = serializer_class.new(model)
        if serializer is not None:
            return serializer
    raise RuntimeError(f'cannot find serializer for {model.__qualname__}')
