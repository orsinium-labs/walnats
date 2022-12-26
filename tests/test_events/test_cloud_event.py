from __future__ import annotations

from datetime import datetime

import walnats


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
