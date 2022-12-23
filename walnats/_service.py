from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator


if TYPE_CHECKING:
    import walnats


@dataclass(frozen=True)
class Service:
    """A single service metainfo, currently used only to draw diagrams.

    Convert it to str or print into stdout to produce a D2 diagram.

    ::

        print(walnats.Service('users', emits=[USER_CREATED]))
    """
    name: str
    emits: walnats.Events | None = None
    defines: walnats.Actors | None = None

    def _iter_lines(self) -> Iterator[str]:
        if self.emits is not None:
            for e in self.emits:
                print(f'{e.name}.shape: oval')
                yield f'{self.name} -> {e.name}: {e.schema.__name__}'
        if self.defines is not None:
            for a in self.defines:
                yield f'{a.event.name} -> {self.name}.{a.name}'

    def __str__(self) -> str:
        return '\n'.join(self._iter_lines())
