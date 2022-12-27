"""Nats-based event-driven background jobs and microservices framework.
"""
from . import middlewares, serializers, types
from ._actors import Actor, Actors, Priority
from ._events import CloudEvent, Event, Events, Limits, Scheduler
from ._services import Services


__version__ = '0.1.0'
__all__ = [
    # classes
    'Actor',
    'Actors',
    'CloudEvent',
    'Event',
    'Events',
    'Limits',
    'Priority',
    'Scheduler',
    'Services',

    # modules
    'serializers',
    'middlewares',
    'types',
]
