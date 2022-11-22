"""
The module contains internal types that walnats can return from some methods
but you never should instantiate them directly. It can be useful in case
you need any of them for type annotaions in your project.
"""
from ._actors import ConnectedActors
from ._events import BaseEvent, ConnectedEvents, EventWithResponse
from ._context import Context, OkContext, ErrorContext

__all__ = [
    'BaseEvent',
    'ConnectedActors',
    'ConnectedEvents',
    'Context',
    'ErrorContext',
    'EventWithResponse',
    'OkContext',
]
