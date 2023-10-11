""" Multicast DNS Service Discovery for Python, v0.14-wmcbrine
    Copyright 2003 Paul Scott-Murphy, 2014 William McBrine

    This module provides a framework for the use of DNS Service Discovery
    using IP multicast.

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
    USA
"""

import asyncio
import socket
from functools import lru_cache
from typing import List, Set

import ifaddr

from zeroconf import DNSIncoming, DNSQuestion, DNSRecord, Zeroconf
from zeroconf._history import QuestionHistory


class QuestionHistoryWithoutSuppression(QuestionHistory):
    def suppresses(self, question: DNSQuestion, now: float, known_answers: Set[DNSRecord]) -> bool:
        return False


def _inject_responses(zc: Zeroconf, msgs: List[DNSIncoming]) -> None:
    """Inject a DNSIncoming response."""
    assert zc.loop is not None

    async def _wait_for_response():
        for msg in msgs:
            zc.record_manager.async_updates_from_response(msg)

    asyncio.run_coroutine_threadsafe(_wait_for_response(), zc.loop).result()


def _inject_response(zc: Zeroconf, msg: DNSIncoming) -> None:
    """Inject a DNSIncoming response."""
    _inject_responses(zc, [msg])


def _wait_for_start(zc: Zeroconf) -> None:
    """Wait for all sockets to be up and running."""
    assert zc.loop is not None
    asyncio.run_coroutine_threadsafe(zc.async_wait_for_start(), zc.loop).result()


@lru_cache(maxsize=None)
def has_working_ipv6():
    """Return True if if the system can bind an IPv6 address."""
    if not socket.has_ipv6:
        return False

    sock = None
    try:
        sock = socket.socket(socket.AF_INET6)
        sock.bind(('::1', 0))
    except Exception:
        return False
    finally:
        if sock:
            sock.close()

    for iface in ifaddr.get_adapters():
        for addr in iface.ips:
            if addr.is_IPv6 and iface.index is not None:
                return True
    return False


def _clear_cache(zc: Zeroconf) -> None:
    zc.cache.cache.clear()
    zc.question_history.clear()
