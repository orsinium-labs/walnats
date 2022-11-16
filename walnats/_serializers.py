from __future__ import annotations

import dataclasses
import datetime
import json
from typing import TYPE_CHECKING, Generic, TypeVar

try:
    import pydantic
except ImportError:
    pydantic = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from pydantic import BaseModel


Model = object
M = TypeVar('M', bound=Model)


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


@dataclasses.dataclass(frozen=True)
class PydanticSerializer(Serializer['BaseModel']):
    """Serialize pydantic models as JSON.
    """
    model: type[BaseModel]

    @classmethod
    def new(cls, model: type[Model]) -> PydanticSerializer | None:
        if pydantic is None:
            return None
        if not issubclass(model, pydantic.BaseModel):
            return None
        return cls(model)

    def encode(self, message: BaseModel) -> bytes:
        return message.json().encode()

    def decode(self, data: bytes) -> BaseModel:
        return self.model.parse_raw(data)


@dataclasses.dataclass(frozen=True)
class DataclassSerializer(Serializer[object]):
    """Serialize dataclass classes as JSON.
    """
    model: type[object]

    @classmethod
    def new(cls, model: type[Model]) -> DataclassSerializer | None:
        if dataclasses.is_dataclass(model):
            return cls(model)
        return None

    def encode(self, message: object) -> bytes:
        payload = dataclasses.asdict(message)
        return json.dumps(payload).encode()

    def decode(self, data: bytes) -> object:
        payload = json.loads(data)
        return self.model(**payload)


@dataclasses.dataclass(frozen=True)
class BytesSerializer(Serializer[bytes]):
    """Assume bytes to be already serialized, emit it as is.
    """
    model: type[bytes]

    @classmethod
    def new(cls, model: type[Model]) -> BytesSerializer | None:
        if issubclass(model, bytes):
            return cls(model)
        return None

    def encode(self, message: bytes) -> bytes:
        return message

    def decode(self, data: bytes) -> bytes:
        return data


@dataclasses.dataclass(frozen=True)
class PrimitiveSerializer(Serializer[object]):
    """Serialize built-in types as JSON.
    """
    model: type[object]

    @classmethod
    def new(cls, model: type[Model]) -> PrimitiveSerializer | None:
        # tuple and set aren't supported by JSON, will be converted into list,
        # and so won't survive roundtrip. Hence it's better not to support them
        # and let the user convert the message type. Otherwise, we won't get type safety.
        if issubclass(model, (str, int, float, list, dict, bool)):
            return cls(model)
        return None

    def encode(self, message: object) -> bytes:
        return json.dumps(message).encode()

    def decode(self, data: bytes) -> object:
        return json.loads(data)


@dataclasses.dataclass(frozen=True)
class DatetimeSerializer(Serializer[datetime.datetime | datetime.date]):
    """Serialize built-in types as JSON.
    """
    model: type[datetime.datetime | datetime.date]

    @classmethod
    def new(cls, model: type[Model]) -> DatetimeSerializer | None:
        # tuple and set aren't supported by JSON, will be converted into list,
        # and so won't survive roundtrip. Hence it's better not to support them
        # and let the user convert the message type. Otherwise, we won't get type safety.
        if issubclass(model, (datetime.datetime, datetime.date)):
            return cls(model)
        return None

    def encode(self, message: datetime.datetime | datetime.date) -> bytes:
        return message.isoformat().encode()

    def decode(self, data: bytes) -> datetime.datetime | datetime.date:
        return self.model.fromisoformat(data.decode())


SERIALIZERS: tuple[type[Serializer], ...] = (
    PydanticSerializer,
    DataclassSerializer,
    BytesSerializer,
    DatetimeSerializer,
    PrimitiveSerializer,
)


def get_serializer(model: type[M]) -> Serializer[M]:
    for serializer_class in SERIALIZERS:
        serializer = serializer_class.new(model)
        if serializer is not None:
            return serializer
    raise RuntimeError(f'cannot find serializer for {model.__qualname__}')
