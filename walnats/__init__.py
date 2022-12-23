"""Nats-based event-driven background jobs and microservices framework.
"""
from . import middlewares, serializers, types
from ._actors import Actor, Actors
from ._events import CloudEvent, Event, Events, Limits
from ._service import Service


__version__ = '0.1.0'
__all__ = [
    # classes
    'Actor',
    'Actors',
    'CloudEvent',
    'Event',
    'Events',
    'Limits',
    'Service',

    # modules
    'serializers',
    'middlewares',
    'types',
]
