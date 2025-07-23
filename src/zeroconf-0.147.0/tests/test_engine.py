"""Unit tests for zeroconf._engine"""

from __future__ import annotations

import asyncio
import itertools
import logging
from unittest.mock import patch

import pytest

import zeroconf as r
from zeroconf import _engine, const
from zeroconf.asyncio import AsyncZeroconf

log = logging.getLogger("zeroconf")
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


# This test uses asyncio because it needs to access the cache directly
# which is not threadsafe
@pytest.mark.asyncio
async def test_reaper():
    with patch.object(_engine, "_CACHE_CLEANUP_INTERVAL", 0.01):
        aiozc = AsyncZeroconf(interfaces=["127.0.0.1"])
        zeroconf = aiozc.zeroconf
        cache = zeroconf.cache
        original_entries = list(itertools.chain(*(cache.entries_with_name(name) for name in cache.names())))
        record_with_10s_ttl = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 10, b"a")
        record_with_1s_ttl = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"b")
        zeroconf.cache.async_add_records([record_with_10s_ttl, record_with_1s_ttl])
        question = r.DNSQuestion("_hap._tcp._local.", const._TYPE_PTR, const._CLASS_IN)
        now = r.current_time_millis()
        other_known_answers: set[r.DNSRecord] = {
            r.DNSPointer(
                "_hap._tcp.local.",
                const._TYPE_PTR,
                const._CLASS_IN,
                10000,
                "known-to-other._hap._tcp.local.",
            )
        }
        zeroconf.question_history.add_question_at_time(question, now, other_known_answers)
        assert zeroconf.question_history.suppresses(question, now, other_known_answers)
        entries_with_cache = list(itertools.chain(*(cache.entries_with_name(name) for name in cache.names())))
        await asyncio.sleep(1.2)
        entries = list(itertools.chain(*(cache.entries_with_name(name) for name in cache.names())))
        assert zeroconf.cache.get(record_with_1s_ttl) is None
        await aiozc.async_close()
        assert not zeroconf.question_history.suppresses(question, now, other_known_answers)
        assert entries != original_entries
        assert entries_with_cache != original_entries
        assert record_with_10s_ttl in entries
        assert record_with_1s_ttl not in entries


@pytest.mark.asyncio
async def test_reaper_aborts_when_done():
    """Ensure cache cleanup stops when zeroconf is done."""
    with patch.object(_engine, "_CACHE_CLEANUP_INTERVAL", 0.01):
        aiozc = AsyncZeroconf(interfaces=["127.0.0.1"])
        zeroconf = aiozc.zeroconf
        record_with_10s_ttl = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 10, b"a")
        record_with_1s_ttl = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"b")
        zeroconf.cache.async_add_records([record_with_10s_ttl, record_with_1s_ttl])
        assert zeroconf.cache.get(record_with_10s_ttl) is not None
        assert zeroconf.cache.get(record_with_1s_ttl) is not None
        await aiozc.async_close()
        await asyncio.sleep(1.2)
        assert zeroconf.cache.get(record_with_10s_ttl) is not None
        assert zeroconf.cache.get(record_with_1s_ttl) is not None
