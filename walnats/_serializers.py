from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

try:
    import pydantic
except ImportError:
    pydantic = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from pydantic import BaseModel


Model = object
M = TypeVar('M', bound=Model)


@dataclass(frozen=True)
class Serializer(Generic[M]):
    model: type[M]

    @classmethod
    def new(cls, model: type[M]) -> Serializer[M] | None:
        raise NotImplementedError

    def encode(self, message: M) -> bytes:
        raise NotImplementedError

    def decode(self, data: bytes) -> M:
        raise NotImplementedError


@dataclass(frozen=True)
class PydanticSerializer(Serializer['BaseModel']):
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


SERIALIZERS: tuple[type[Serializer], ...] = (
    PydanticSerializer,
)


def get_serializer(model: type[M]) -> Serializer[M]:
    for serializer_class in SERIALIZERS:
        serializer = serializer_class.new(model)
        if serializer is not None:
            return serializer
    raise RuntimeError(f'cannot find serializer for {model.__qualname__}')
