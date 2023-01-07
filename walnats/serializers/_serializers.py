from __future__ import annotations

import dataclasses
import datetime
import json
from typing import TYPE_CHECKING

from ._base import Serializer


try:
    import pydantic
except ImportError:
    pydantic = None  # type: ignore[assignment]

try:
    import google.protobuf.message as protobuf
except ImportError:
    protobuf = None  # type: ignore[assignment]

try:
    import marshmallow
except ImportError:
    marshmallow = None  # type: ignore[assignment]


if TYPE_CHECKING:
    from google.protobuf.message import Message as ProtobufMessage
    from marshmallow import Schema as MarshmallowSchema
    from pydantic import BaseModel


@dataclasses.dataclass(frozen=True)
class PydanticSerializer(Serializer['BaseModel']):
    """Serialize pydantic models as JSON.
    """
    schema: type[BaseModel]

    @classmethod
    def new(cls, schema: type[object]) -> PydanticSerializer | None:
        if pydantic is None:
            return None
        if not issubclass(schema, pydantic.BaseModel):
            return None
        return cls(schema)

    def encode(self, message: BaseModel) -> bytes:
        return message.json(separators=(',', ':')).encode(encoding='utf8')

    def decode(self, data: bytes) -> BaseModel:
        return self.schema.parse_raw(data)


@dataclasses.dataclass(frozen=True)
class DataclassSerializer(Serializer[object]):
    """Serialize dataclass classes as JSON.
    """
    schema: type[object]

    @classmethod
    def new(cls, schema: type[object]) -> DataclassSerializer | None:
        if dataclasses.is_dataclass(schema):
            return cls(schema)
        return None

    def encode(self, message: object) -> bytes:
        payload = dataclasses.asdict(message)
        return json.dumps(payload, separators=(',', ':')).encode(encoding='utf8')

    def decode(self, data: bytes) -> object:
        payload = json.loads(data)
        return self.schema(**payload)


@dataclasses.dataclass(frozen=True)
class MarshmallowSerializer(Serializer['MarshmallowSchema']):
    """Serialize marshmallow schemas as JSON.

    If you use marshmallow schemas for events, you'll get false-positives from mypy
    on actors because the data you serialize with a marshmallow schema has a dict type,
    not the schema type. If you care about type safety, use dtaclasses or pydantic
    for models instead. If you can't, throw in ``# type: ignore`` where is applicable.
    """
    schema: type[MarshmallowSchema]

    @classmethod
    def new(cls, schema: type[object]) -> MarshmallowSerializer | None:
        if marshmallow is None:
            return None
        if not issubclass(schema, marshmallow.Schema):
            return None
        return cls(schema)

    def encode(self, message: MarshmallowSchema) -> bytes:
        return self.schema().dumps(message).encode(encoding='utf8')

    def decode(self, data: bytes) -> MarshmallowSchema:
        return self.schema().loads(data.decode(encoding='utf8'))


@dataclasses.dataclass(frozen=True)
class BytesSerializer(Serializer[bytes]):
    """Assume bytes to be already serialized, emit it as is.
    """
    schema: type[bytes]

    @classmethod
    def new(cls, schema: type[object]) -> BytesSerializer | None:
        if issubclass(schema, bytes):
            return cls(schema)
        return None

    def encode(self, message: bytes) -> bytes:
        return message

    def decode(self, data: bytes) -> bytes:
        return data


@dataclasses.dataclass(frozen=True)
class PrimitiveSerializer(Serializer[object]):
    """Serialize built-in types as JSON.
    """
    schema: type[object]

    @classmethod
    def new(cls, schema: type[object]) -> PrimitiveSerializer | None:
        # tuple and set aren't supported by JSON, will be converted into list,
        # and so won't survive roundtrip. Hence it's better not to support them
        # and let the user convert the message type. Otherwise, we won't get type safety.
        if issubclass(schema, (str, int, float, list, dict, bool)):
            return cls(schema)
        if schema is None or issubclass(schema, type(None)):
            return cls(schema)
        return None

    def encode(self, message: object) -> bytes:
        return json.dumps(message, separators=(',', ':')).encode(encoding='utf8')

    def decode(self, data: bytes) -> object:
        return json.loads(data)


@dataclasses.dataclass(frozen=True)
class DatetimeSerializer(Serializer['datetime.datetime | datetime.date']):
    """Serialize datetime or date in ISO 8601 string.
    """
    schema: type[datetime.datetime | datetime.date]

    @classmethod
    def new(cls, schema: type[object]) -> DatetimeSerializer | None:
        # tuple and set aren't supported by JSON, will be converted into list,
        # and so won't survive roundtrip. Hence it's better not to support them
        # and let the user convert the message type. Otherwise, we won't get type safety.
        if issubclass(schema, (datetime.datetime, datetime.date)):
            return cls(schema)
        return None

    def encode(self, message: datetime.datetime | datetime.date) -> bytes:
        return message.isoformat().encode(encoding='utf8')

    def decode(self, data: bytes) -> datetime.datetime | datetime.date:
        return self.schema.fromisoformat(data.decode())


@dataclasses.dataclass(frozen=True)
class ProtobufSerializer(Serializer['ProtobufMessage']):
    """Serialize protobuf messages.
    """
    schema: type[ProtobufMessage]

    @classmethod
    def new(cls, schema: type[object]) -> ProtobufSerializer | None:
        if protobuf is None:
            return None
        if issubclass(schema, protobuf.Message):
            return cls(schema)
        return None

    def encode(self, message: ProtobufMessage) -> bytes:
        return message.SerializeToString()

    def decode(self, data: bytes) -> ProtobufMessage:
        return self.schema.FromString(data)
