from __future__ import annotations

import datetime
from dataclasses import dataclass

import marshmallow
import pydantic
import pytest
from cryptography.fernet import Fernet, InvalidToken

import walnats

from .protobuf_pb2 import Protobuf  # type: ignore [attr-defined]


class Pydantic(pydantic.BaseModel):
    value: str


@dataclass
class Dataclass:
    value: str


TEST_CASES = [
    Pydantic(value='hi'),
    Dataclass(value='hi'),
    Protobuf(value='hello'),
    'hello',
    b'hello',
    123,
    123.45,
    True,
    None,
    ['hello', 'world'],
    {'hello': 'world'},
    datetime.date.today(),
    datetime.datetime.now(),
]


@pytest.mark.parametrize('message', TEST_CASES)
def test_roundtrip(message: object) -> None:
    assert message == message  # test if comparable
    schema = type(message)
    ser = walnats.serializers.get_serializer(schema)
    enc = ser.encode(message)
    dec = ser.decode(enc)
    assert message == dec


def test_marshmallow_roundtrip():
    class Marshmallow(marshmallow.Schema):
        value = marshmallow.fields.Str()

    ser = walnats.serializers.get_serializer(Marshmallow)
    message = {'value': 'hello'}
    enc = ser.encode(message)  # type: ignore[arg-type]
    dec = ser.decode(enc)
    assert message == dec  # type: ignore[comparison-overlap]


@pytest.mark.parametrize('message', TEST_CASES)
def test_gzip_roundtrip(message: object) -> None:
    assert message == message
    schema = type(message)
    orig_ser = walnats.serializers.get_serializer(schema)
    gzip_ser = walnats.serializers.GZipSerializer(schema=schema, serializer=orig_ser)

    orig_enc = orig_ser.encode(message)
    enc = gzip_ser.encode(message)
    assert enc != orig_enc

    dec = gzip_ser.decode(enc)
    assert message == dec


@pytest.mark.parametrize('message', [
    'hello',
    b'hello',
    123,
    123.45,
    True,
    ['hello', 'world'],
    {'hello': 'world'},
])
def test_message_pack_roundtrip(message: object) -> None:
    assert message == message
    schema = type(message)
    ser = walnats.serializers.MessagePackSerializer(schema=schema)
    enc = ser.encode(message)
    assert isinstance(enc, bytes)
    dec = ser.decode(enc)
    assert message == dec


@pytest.mark.parametrize('message', TEST_CASES)
def test_hmac_roundtrip(message: object) -> None:
    assert message == message
    schema = type(message)
    orig_ser = walnats.serializers.get_serializer(schema)
    hmac_ser = walnats.serializers.HMACSerializer(
        schema=schema,
        serializer=orig_ser,
        key=b'secret',
    )

    orig_enc = orig_ser.encode(message)
    enc = hmac_ser.encode(message)
    assert enc != orig_enc

    dec = hmac_ser.decode(enc)
    assert message == dec

    with pytest.raises(ValueError, match='the message is corrupted or altered'):
        hmac_ser.decode(enc + b'a')
    with pytest.raises(ValueError, match='the message is corrupted or altered'):
        hmac_ser.decode(b'a' + enc)


@pytest.mark.parametrize('message', TEST_CASES)
def test_fernet_roundtrip(message: object) -> None:
    assert message == message
    schema = type(message)
    orig_ser = walnats.serializers.get_serializer(schema)
    key = Fernet.generate_key()
    fernet_ser = walnats.serializers.FernetSerializer(
        schema=schema,
        serializer=orig_ser,
        key=key,
    )

    orig_enc = orig_ser.encode(message)
    enc = fernet_ser.encode(message)
    assert enc != orig_enc

    dec = fernet_ser.decode(enc)
    assert message == dec

    with pytest.raises(InvalidToken):
        fernet_ser.decode(b'a' + enc)


def test_no_serializer():
    with pytest.raises(LookupError):
        walnats.serializers.get_serializer(object)
