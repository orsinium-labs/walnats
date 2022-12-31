from __future__ import annotations

from datetime import datetime

import hypothesis
import hypothesis.strategies
import pytest

import walnats


@hypothesis.given(
    dt=hypothesis.strategies.datetimes(),
)
def test_filter_time__no_filter(dt: datetime) -> None:
    called = False

    @walnats.decorators.filter_time()
    def handler(event: datetime) -> None:
        nonlocal called
        called = True
        assert event == dt

    handler(dt)
    assert called


def make_dt(**kwargs) -> datetime:
    return datetime.now().replace(**kwargs)


@pytest.mark.parametrize('given, dt, expected', [
    (dict(hour=4), make_dt(hour=4), True),
    (dict(hour=4), make_dt(hour=5), False),
    (dict(hour=4), make_dt(hour=16), False),

    (dict(hour=16), make_dt(hour=16), True),
    (dict(hour=16), make_dt(hour=4), False),
    (dict(hour=16), make_dt(hour=5), False),

    (dict(year=2024, day=1), make_dt(year=2024, day=1), True),
    (dict(year=2024, day=1), make_dt(year=2024, day=2), False),
    (dict(year=2024, day=1), make_dt(year=2025, day=1), False),
    (dict(year=2024, day=1), make_dt(year=2025, day=2), False),
])
def test_filter_time(given: dict, dt: datetime, expected: bool) -> None:
    called = False

    @walnats.decorators.filter_time(**given)
    def handler(event: datetime) -> None:
        nonlocal called
        called = True
        assert event == dt

    handler(dt)
    assert called is expected
