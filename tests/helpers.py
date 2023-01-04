from __future__ import annotations

import asyncio
import re
import socket
import time
from collections import Counter
from contextlib import contextmanager
from random import choice
from string import ascii_letters

import walnats


class UDPLogProtocol(asyncio.DatagramProtocol):
    port: int

    def __init__(self, port: int):
        self.hist: list[str] = []
        self.port = port
        super().__init__()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        self.hist.append(data.decode('utf8'))


def get_random_port() -> int:
    sock = socket.socket()
    sock.bind(('', 0))
    return sock.getsockname()[1]


def get_random_name() -> str:
    return ''.join(choice(ascii_letters) for _ in range(20))


def fuzzy_match_counter(items: list[str], rules: list[tuple[str, int]]):
    counter = Counter(items)
    print(counter)
    len_counter = len(counter.most_common())
    len_rules = len(rules)
    assert len_counter == len_rules, f'{len_counter} != {len_rules}'
    for act, exp in zip(counter.most_common(), rules):
        act_val, act_count = act
        exp_val, exp_count = exp
        act_val = act_val.rstrip()
        assert re.fullmatch(exp_val, act_val), f'{repr(act_val)} ~= /{exp_val}/'
        assert act_count == exp_count, f'{act_count} != {exp_count}'


async def run_burst(
    *actors: walnats.Actor,
    messages: list[tuple[walnats.Event[str], str]],
    **kwargs,
) -> None:
    events_names = set()
    events: list[walnats.types.BaseEvent] = []
    e: walnats.types.BaseEvent
    for e, _ in messages:
        if e.name not in events_names:
            events.append(e)
            events_names.add(e.name)
    for a in actors:
        e = a.event
        if e.name not in events_names:
            events.append(e)
            events_names.add(e.name)

    events_reg = walnats.Events(*events)
    actors_reg = walnats.Actors(*actors)
    async with events_reg.connect() as pub_conn, actors_reg.connect() as sub_conn:
        await pub_conn.register()
        await sub_conn.register()
        await asyncio.gather(*[pub_conn.emit(e, m) for e, m in messages])
        await asyncio.sleep(.01)
        await sub_conn.listen(burst=True, **kwargs)


@contextmanager
def duration_between(min_dur: float, max_dur: float):
    start = time.perf_counter()
    yield
    actual_dur = time.perf_counter() - start
    assert min_dur <= actual_dur < max_dur, f'time spent: {actual_dur}'
