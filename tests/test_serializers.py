import datetime
from dataclasses import dataclass

import pydantic
import pytest

from walnats.serializers import get_serializer


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
def test_roundtrip(message) -> None:
    assert message == message
    model = type(message)
    ser = get_serializer(model)
    enc = ser.encode(message)
    dec = ser.decode(enc)
    assert message == dec
