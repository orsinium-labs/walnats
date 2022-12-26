from __future__ import annotations

import pytest

import walnats


@pytest.mark.parametrize('given, expected', [
    (dict(), ['time.*.*.*.*.*']),
    (dict(hour=4), ['time.*.*.*.04.*']),
    (dict(month=2, prefix='date'), ['date.*.02.*.*.*']),
    (dict(year=2022, day=1), ['time.2022.*.01.*.*']),
    (dict(hour=16), ['time.*.*.*.16.*']),
    (dict(hour=16, minute=3), ['time.*.*.*.16.03']),
    (dict(hour=(4, 5)), ['time.*.*.*.04.*', 'time.*.*.*.05.*']),
    (
        dict(hour=(4, 5), minute=(6, 7)),
        [
            'time.*.*.*.04.06', 'time.*.*.*.04.07',
            'time.*.*.*.05.06', 'time.*.*.*.05.07',
        ],
    ),
])
def test_Event_with_schedule(given: dict, expected: list[str]) -> None:
    e = walnats.Event('', str).with_schedule(**given)
    assert e.patterns == expected
