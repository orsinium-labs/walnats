from __future__ import annotations

import walnats


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
