"""Example of drawing d2 diagrams of walnats-based architecture.

Usage:
    python3 ./examples/diagram.py | d2 - > arch.svg
    chromium ./arch.svg
"""

from __future__ import annotations
from dataclasses import dataclass
import walnats


@dataclass
class User:
    id: int
    name: str


class Email:
    id: int
    receiver: str


def noop(_: object) -> None:
    pass


USER_CREATED = walnats.Event('user-created', User)
USER_UPDATED = walnats.Event('user-updated', User)
EMAIL_SENT = walnats.Event('email-sent', Email)

services = [
    walnats.Service(
        name='users',
        emits=walnats.Events(USER_CREATED, USER_UPDATED),
    ),
    walnats.Service(
        name='notifications',
        emits=walnats.Events(EMAIL_SENT),
        defines=walnats.Actors(
            walnats.Actor('send-email', USER_CREATED, noop),
            walnats.Actor('send-email', USER_UPDATED, noop),
            walnats.Actor('send-sms', USER_CREATED, noop),
            walnats.Actor('send-sms', USER_UPDATED, noop),
        ),
    ),
    walnats.Service(
        name='audit-log',
        defines=walnats.Actors(
            walnats.Actor('record', USER_CREATED, noop),
            walnats.Actor('record', EMAIL_SENT, noop),
        ),
    ),
]

print('direction: right')
for s in services:
    print(s)
