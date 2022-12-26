from __future__ import annotations

import walnats

from ..helpers import get_random_name


def test_events_get():
    events = walnats.Events(
        walnats.Event('e1', str),
        walnats.Event('e2', str),
        walnats.Event('e3', str),
    )
    e1 = events.get('e1')
    assert e1
    assert e1.name == 'e1'
    e2 = events.get('e2')
    assert e2
    assert e2.name == 'e2'
    assert events.get('something') is None


def test_events_iter():
    e1 = walnats.Event(get_random_name(), str)
    e2 = walnats.Event(get_random_name(), str)
    e3 = walnats.Event(get_random_name(), str)
    events = walnats.Events(e1, e2, e3)
    assert list(events) == [e1, e2, e3]
