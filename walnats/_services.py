from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator


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

    Currently, can produce the following specifications:

    * `Event storming <https://en.wikipedia.org/wiki/Event_storming>`_ diagram
      as `d2 <https://github.com/terrastruct/d2>`_ definition.
    * `AsyncAPI <https://www.asyncapi.com/>`_ spec either for each service
      or all services combined.

    ::

        services = walnats.Services()

    """
    _services: list[Service] = field(default_factory=list, init=False)

    def add(
        self,
        name: str, *,
        version: str = '0.0.0',
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
        self._services.append(Service(name, version, emits, defines))

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

    def get_async_apis(self) -> list[dict[str, Any]]:
        """Generate an AsyncAPI schema for every service.

        Returns a list of valid `AsyncAPI <https://www.asyncapi.com/>`_ schemas
        for each service.


        ::

            specs = services.get_async_api()
            for spec in specs:
                service_name = spec['info']['title']
                with open(f'{service_name}.json') as f:
                    json.dump(spec, f)

        """
        return [s.get_async_api() for s in self._services]

    def get_async_api(self) -> dict[str, Any]:
        """Generate a combined AsyncAPI schema for all services.

        It's simply a merge of all events that all services emit
        plus a few required field on top of that to produce a valid schema.
        It's generally a good idea to add more info into it before saving the result
        into a JSON or YAML file.

        ::

            spec = services.get_async_api()
            spec['info']['description'] = 'Here comes the sun'
            with open('spec.json') as f:
                json.dump(spec, f)

        """
        channels = {}
        schemas = {}
        for s in self._services:
            service_spec = s.get_async_api()
            channels.update(service_spec['channels'])
            schemas.update(service_spec['components']['schemas'])
        return {
            'asyncapi': '2.5.0',
            'info': {
                'title': 'application',
                'version': '0.0.0',
            },
            'channels': channels,
            'components': {'schemas': schemas},
        }


@dataclass(frozen=True)
class Service:
    """Internal class to represent a single service in a microservice arch.
    """
    name: str
    version: str
    emits: walnats.Events | None
    defines: walnats.Actors | None

    def d2_iter_lines(self, colors: bool) -> Iterator[str]:
        """Produce lines for d2 diagram definition.
        """
        if colors:
            yield f'{self.name}.style: {SERVICE_STYLE}'
        for e in (self.emits or []):
            yield f'{e.name}.shape: oval'
            if colors:
                yield f'{e.name}.style: {EVENT_STYLE}'
            yield f'{self.name} -> {e.name}: {e.schema.__name__}'
        for a in (self.defines or []):
            if colors:
                yield f'{a.event.name} -> {self.name}.{a.name}: {ARROW_STYLE}'
            else:
                yield f'{a.event.name} -> {self.name}.{a.name}'
            if colors:
                yield f'{self.name}.{a.name}.style: {ACTOR_STYLE}'

    def get_async_api(self) -> dict[str, Any]:
        """Produce AsyncAPI spec for the service.
        """
        channels: dict[str, dict[str, Any]] = {}
        schemas: dict[str, dict[str, Any]] = {}
        for event in (self.emits or []):
            schema_name = event.schema.__name__
            edef: dict[str, Any] = {
                'subscribe': {
                    'message': {
                        'name': schema_name,
                        'payload': {'$ref': f'#/components/schemas/{schema_name}'},
                    },
                },
            }
            if event.description:
                edef['description'] = event.description
            channels[event.name] = edef
            schemas[schema_name] = {'type': 'object'}

        return {
            'asyncapi': '2.5.0',
            'info': {
                'title': self.name,
                'version': self.version,
            },
            'channels': channels,
            'components': {'schemas': schemas},
        }
