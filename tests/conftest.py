from __future__ import annotations
import asyncio

import pytest
from .helpers import random_port, UDPLogProtocol


@pytest.fixture
async def udp_server():
    port = random_port()
    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPLogProtocol(port),
        local_addr=('127.0.0.1', port),
    )
    yield protocol
    transport.close()
