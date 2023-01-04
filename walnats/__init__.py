"""Nats-based event-driven background jobs and microservices framework.
"""
from . import decorators, middlewares, serializers, types
from ._actors import Actor, Actors, Priority
from ._errors import ConsumerExistsError, StreamConfigError, StreamExistsError
from ._events import Clock, CloudEvent, Event, Events, Limits
from ._services import Services


__version__ = '0.1.0'
__all__ = [
    # classes
    'Actor',
    'Actors',
    'Clock',
    'CloudEvent',
    'Event',
    'Events',
    'Limits',
    'Priority',
    'Services',

    # exceptions
    'ConsumerExistsError',
    'StreamConfigError',
    'StreamExistsError',

    # modules
    'decorators',
    'serializers',
    'middlewares',
    'types',
]
