from __future__ import annotations

import datetime
from dataclasses import dataclass

import pydantic
import pytest

from walnats.serializers import Serializer, get_serializer


class Pydantic(pydantic.BaseModel):
    value: str


@dataclass
class Dataclass:
    value: str


@pytest.mark.parametrize('message', [
    Pydantic(value='hi'),
    Dataclass(value='hi'),
    'hello',
    b'hello',
    123,
    123.45,
    True,
    ['hello', 'world'],
    {'hello': 'world'},
    datetime.date.today(),
    datetime.datetime.now(),
])
def test_roundtrip(message: object) -> None:
    assert message == message
    schema = type(message)
    ser: Serializer[object] = get_serializer(schema)
    enc = ser.encode(message)
    dec = ser.decode(enc)
    assert message == dec
