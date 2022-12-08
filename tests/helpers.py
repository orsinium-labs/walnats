from __future__ import annotations
from collections import Counter
from random import choice
from string import ascii_letters
import asyncio
import re
import socket


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


def random_port() -> int:
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
