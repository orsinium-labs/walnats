from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator


if TYPE_CHECKING:
    import walnats


@dataclass(frozen=True)
class Services:
    """A description of services that your system has.

    It doesn't serve any direct practical purpose. Walnats doesn't care what services
    you have or where events are emitted from. The purpose of Services is to describe
    your system for producing architectural overview in a form of diagrams and specs.

    ::

        services = walnats.Services()

    """
    _services: list[Service] = field(default_factory=list)

    def add(
        self,
        name: str, *,
        emits: walnats.Events | None = None,
        defines: walnats.Actors | None = None,
    ):
        """Add a service.

        The service is described by the ``name`` it has, events it ``emits``,
        and actors it ``defines``.

        ::

            services.add(
                name='users',
                emits=walnats.Events(USER_CREATED, USER_UPDATED),
            )
            services.add(
                name='notifications',
                defines=walnats.Actors(SEND_EMAIL),
            )

        """
        self._services.append(Service(name, emits, defines))

    def get_d2(self, direction: str = 'right') -> str:
        """Generate a d2 diagram definition.

        `D2 <https://github.com/terrastruct/d2>` is a language for generating diagrams,
        similar to PlantUML or GraphViz (see `comparison <https://text-to-diagram.com/>`).
        This method produces a diagram definition that you can pipe into d2 CLI
        to generate an actual image.

        In the script (``arch.py``):

        ::

            print(services.get_d2())

        And then run in shell:

        ::

            python3 arch.py | d2 - > arch.svg

        """
        return '\n'.join(self._d2_iter_lines(direction=direction))

    def _d2_iter_lines(self, direction: str) -> Iterator[str]:
        yield f'direction: {direction}'
        for s in self._services:
            yield from s.d2_iter_lines()


@dataclass(frozen=True)
class Service:
    name: str
    emits: walnats.Events | None = None
    defines: walnats.Actors | None = None

    def d2_iter_lines(self) -> Iterator[str]:
        if self.emits is not None:
            for e in self.emits:
                print(f'{e.name}.shape: oval')
                yield f'{self.name} -> {e.name}: {e.schema.__name__}'
        if self.defines is not None:
            for a in self.defines:
                yield f'{a.event.name} -> {self.name}.{a.name}'
