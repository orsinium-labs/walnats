from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator


if TYPE_CHECKING:
    from typing import Literal

    import walnats

# https://en.wikipedia.org/wiki/Event_storming#Example_notes
ACTOR_STYLE = '{stroke: "#2980b9"; fill: "#e9f2fb"}'
SERVICE_STYLE = '{stroke: "#f39c12"; fill: "#fef4e6"}'
EVENT_STYLE = '{stroke: "#e74c3c"; fill: "#fcebea"}'
ARROW_STYLE = '{style: {stroke: "#2c3e50"}}'


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

    def get_d2(
        self,
        direction: Literal['left', 'right', 'down', 'up'] = 'right',
        colors: bool = True,
    ) -> str:
        """Generate a d2 diagram definition.

        `D2 <https://github.com/terrastruct/d2>`_ is a language for generating diagrams,
        similar to PlantUML or GraphViz
        (see `comparison <https://text-to-diagram.com/>`_).
        This method produces a diagram definition that you can pipe into d2 CLI
        to generate an actual image.

        Args:
            direction: direction of drawing the diagram, in the order as services
                are defined. See `d2 docs <https://d2lang.com/tour/layouts#direction>`_.
            colors: whatever to explicitly specify colors. If enabled (default),
                `event storming <https://en.wikipedia.org/wiki/Event_storming>`_
                colors will be used for elements. If disabled, the colors are controlled
                by the `d2 theme <https://d2lang.com/tour/themes>`_.

        In the script (``arch.py``):

        ::

            print(services.get_d2())

        And then run in shell:

        ::

            python3 arch.py | d2 - > arch.svg

        """
        return '\n'.join(self._d2_iter_lines(
            direction=direction,
            colors=colors,
        ))

    def _d2_iter_lines(self, direction: str, colors: bool) -> Iterator[str]:
        yield f'direction: {direction}'
        for s in self._services:
            yield from s.d2_iter_lines(colors=colors)


@dataclass(frozen=True)
class Service:
    name: str
    emits: walnats.Events | None = None
    defines: walnats.Actors | None = None

    def d2_iter_lines(self, colors: bool) -> Iterator[str]:
        if colors:
            yield f'{self.name}.style: {SERVICE_STYLE}'

        if self.emits is not None:
            for e in self.emits:
                yield f'{e.name}.shape: oval'
                if colors:
                    yield f'{e.name}.style: {EVENT_STYLE}'
                yield f'{self.name} -> {e.name}: {e.schema.__name__}'

        if self.defines is not None:
            for a in self.defines:
                if colors:
                    yield f'{a.event.name} -> {self.name}.{a.name}: {ARROW_STYLE}'
                else:
                    yield f'{a.event.name} -> {self.name}.{a.name}'
                if colors:
                    yield f'{self.name}.{a.name}.style: {ACTOR_STYLE}'
