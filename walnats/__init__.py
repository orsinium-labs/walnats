"""Nats-based event-driven background jobs and microservices framework.
"""
from . import middlewares, serializers, types
from ._actors import Actor, Actors
from ._diagrams import Service, Services
from ._events import Event, Events, Limits


__version__ = '0.1.0'
__all__ = [
    # classes
    'Actor',
    'Actors',
    'Event',
    'Events',
    'Limits',
    'Service',
    'Services',

    # modules
    'serializers',
    'middlewares',
    'types',
]
