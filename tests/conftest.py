from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
from shutil import which

import pytest

import walnats

from .helpers import UDPLogProtocol, get_random_name, get_random_port


@pytest.fixture(autouse=True, scope='session')
def run_nats_server():
    exe = 'nats-server'
    if not which(exe):
        exe = str(Path.home() / 'go' / 'bin' / 'nats-server')
    if not which(exe):
        raise RuntimeError('nats-server must be in PATH')
    proc = subprocess.Popen([exe, '--jetstream'], stdout=subprocess.DEVNULL)
    assert proc.returncode is None
    yield
    assert proc.returncode is None
    proc.kill()


@pytest.fixture
async def udp_server():
    port = get_random_port()
    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPLogProtocol(port),
        local_addr=('127.0.0.1', port),
    )
    yield protocol
    transport.close()


@pytest.fixture
async def event() -> walnats.Event[str]:
    return walnats.Event(get_random_name(), str)


@pytest.fixture
async def actor(event: walnats.Event[str]) -> walnats.Actor[str, None]:
    return walnats.Actor(get_random_name(), event, lambda _: None)
