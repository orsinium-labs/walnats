import pydantic
import pytest
from walnats._serializers import get_serializer


class Pydantic(pydantic.BaseModel):
    value: str


@pytest.mark.parametrize('message', [
    Pydantic(value='hi'),
])
def test_roundtrip(message) -> None:
    assert message == message
    model = type(message)
    ser = get_serializer(model)
    enc = ser.encode(message)
    dec = ser.decode(enc)
    assert message == dec
