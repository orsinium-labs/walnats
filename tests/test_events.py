from __future__ import annotations

import asyncio
from datetime import datetime

import walnats

from .helpers import get_random_name


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


async def test_events_monitor():
    event = walnats.Event(get_random_name(), str)
    events = walnats.Events(event)
    async with events.connect() as conn:
        with conn.monitor() as monitor:
            asyncio.create_task(conn.emit(event, 'hello'))
            recv = await asyncio.wait_for(monitor.get(), timeout=2)
            assert recv == 'hello'


async def test_CloudEvent_as_headers():
    ce = walnats.CloudEvent(
        id='hi123',
        source='/sensors/tn-123/alerts',
        type='com.example.object.delete.v2',
    )
    assert ce.as_headers() == {
        'ce-id': 'hi123',
        'ce-source': '/sensors/tn-123/alerts',
        'ce-type': 'com.example.object.delete.v2',
        'ce-specversion': '1.0',
    }


async def test_CloudEvent_as_headers__with_time():
    ce = walnats.CloudEvent(
        id='hi123',
        source='/sensors/tn-123/alerts',
        type='com.example.object.delete.v2',
        time=datetime(2023, 12, 31, 23, 59, 54),
    )
    assert ce.as_headers() == {
        'ce-id': 'hi123',
        'ce-source': '/sensors/tn-123/alerts',
        'ce-type': 'com.example.object.delete.v2',
        'ce-specversion': '1.0',
        'ce-time': '2023-12-31T23:59:54Z',
    }
