from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    import walnats


@dataclass(frozen=True)
class Service:
    name: str
    emits: walnats.Events | None = None
    defines: walnats.Actors | None = None

    def iter_lines(self) -> Iterator[str]:
        if self.emits:
            for e in self.emits:
                print(f'{e.name}.shape: oval')
                yield f'{self.name} -> {e.name}: {e.schema.__name__}'
        if self.defines:
            for a in self.defines:
                yield f'{a.event.name} -> {self.name}.{a.name}'

    def __str__(self) -> str:
        return '\n'.join(self.iter_lines())
