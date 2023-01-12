"""Nats-based event-driven background jobs and microservices framework.
"""
from . import decorators, middlewares, serializers, types
from ._actors import Actor, Actors, ExecuteIn, Priority
from ._errors import StreamConfigError, StreamExistsError
from ._events import Clock, CloudEvent, Event, Events, Limits
from ._services import Services


__version__ = '1.2.5'
__all__ = [
    # classes
    'Actor',
    'Actors',
    'Clock',
    'CloudEvent',
    'Event',
    'Events',
    'ExecuteIn',
    'Limits',
    'Priority',
    'Services',

    # exceptions
    'StreamConfigError',
    'StreamExistsError',

    # modules
    'decorators',
    'serializers',
    'middlewares',
    'types',
]
