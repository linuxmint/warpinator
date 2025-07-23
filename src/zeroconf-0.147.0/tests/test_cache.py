"""Unit tests for zeroconf._cache."""

from __future__ import annotations

import logging
import unittest.mock
from heapq import heapify, heappop

import pytest

import zeroconf as r
from zeroconf import const

log = logging.getLogger("zeroconf")
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


class TestDNSCache(unittest.TestCase):
    def test_order(self):
        record1 = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"b")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        entry = r.DNSEntry("a", const._TYPE_SOA, const._CLASS_IN)
        cached_record = cache.get(entry)
        assert cached_record == record2

    def test_adding_same_record_to_cache_different_ttls_with_get(self):
        """We should always get back the last entry we added if there are different TTLs.

        This ensures we only have one source of truth for TTLs as a record cannot
        be both expired and not expired.
        """
        record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 10, b"a")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        entry = r.DNSEntry(record2.name, const._TYPE_A, const._CLASS_IN)
        cached_record = cache.get(entry)
        assert cached_record == record2

    def test_adding_same_record_to_cache_different_ttls_with_get_all(self):
        """Verify we only get one record back.

        The last record added should replace the previous since two
        records with different ttls are __eq__. This ensures we
        only have one source of truth for TTLs as a record cannot
        be both expired and not expired.
        """
        record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 10, b"a")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        cached_records = cache.get_all_by_details("a", const._TYPE_A, const._CLASS_IN)
        assert cached_records == [record2]

    def test_cache_empty_does_not_leak_memory_by_leaving_empty_list(self):
        record1 = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"b")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert "a" in cache.cache
        cache.async_remove_records([record1, record2])
        assert "a" not in cache.cache

    def test_cache_empty_multiple_calls(self):
        record1 = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_SOA, const._CLASS_IN, 1, b"b")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert "a" in cache.cache
        cache.async_remove_records([record1, record2])
        assert "a" not in cache.cache


class TestDNSAsyncCacheAPI(unittest.TestCase):
    def test_async_get_unique(self):
        record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"b")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.async_get_unique(record1) == record1
        assert cache.async_get_unique(record2) == record2

    def test_async_all_by_details(self):
        record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"b")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.async_all_by_details("a", const._TYPE_A, const._CLASS_IN)) == {
            record1,
            record2,
        }

    def test_async_entries_with_server(self):
        record1 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            85,
            "ab",
        )
        record2 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            80,
            "ab",
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.async_entries_with_server("ab")) == {record1, record2}
        assert set(cache.async_entries_with_server("AB")) == {record1, record2}

    def test_async_entries_with_name(self):
        record1 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            85,
            "ab",
        )
        record2 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            80,
            "ab",
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.async_entries_with_name("irrelevant")) == {record1, record2}
        assert set(cache.async_entries_with_name("Irrelevant")) == {record1, record2}


# These functions have been seen in other projects so
# we try to maintain a stable API for all the threadsafe getters
class TestDNSCacheAPI(unittest.TestCase):
    def test_get(self):
        record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"b")
        record3 = r.DNSAddress("a", const._TYPE_AAAA, const._CLASS_IN, 1, b"ipv6")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2, record3])
        assert cache.get(record1) == record1
        assert cache.get(record2) == record2
        assert cache.get(r.DNSEntry("a", const._TYPE_A, const._CLASS_IN)) == record2
        assert cache.get(r.DNSEntry("a", const._TYPE_AAAA, const._CLASS_IN)) == record3
        assert cache.get(r.DNSEntry("notthere", const._TYPE_A, const._CLASS_IN)) is None

    def test_get_by_details(self):
        record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"b")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.get_by_details("a", const._TYPE_A, const._CLASS_IN) == record2

    def test_get_all_by_details(self):
        record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a")
        record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"b")
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.get_all_by_details("a", const._TYPE_A, const._CLASS_IN)) == {
            record1,
            record2,
        }

    def test_entries_with_server(self):
        record1 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            85,
            "ab",
        )
        record2 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            80,
            "ab",
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.entries_with_server("ab")) == {record1, record2}
        assert set(cache.entries_with_server("AB")) == {record1, record2}

    def test_entries_with_name(self):
        record1 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            85,
            "ab",
        )
        record2 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            80,
            "ab",
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.entries_with_name("irrelevant")) == {record1, record2}
        assert set(cache.entries_with_name("Irrelevant")) == {record1, record2}

    def test_current_entry_with_name_and_alias(self):
        record1 = r.DNSPointer(
            "irrelevant",
            const._TYPE_PTR,
            const._CLASS_IN,
            const._DNS_OTHER_TTL,
            "x.irrelevant",
        )
        record2 = r.DNSPointer(
            "irrelevant",
            const._TYPE_PTR,
            const._CLASS_IN,
            const._DNS_OTHER_TTL,
            "y.irrelevant",
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.current_entry_with_name_and_alias("irrelevant", "x.irrelevant") == record1

    def test_name(self):
        record1 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            85,
            "ab",
        )
        record2 = r.DNSService(
            "irrelevant",
            const._TYPE_SRV,
            const._CLASS_IN,
            const._DNS_HOST_TTL,
            0,
            0,
            80,
            "ab",
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.names() == ["irrelevant"]


def test_async_entries_with_name_returns_newest_record():
    cache = r.DNSCache()
    record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=1.0)
    record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    assert next(iter(cache.async_entries_with_name("a"))) is record2


def test_async_entries_with_server_returns_newest_record():
    cache = r.DNSCache()
    record1 = r.DNSService("a", const._TYPE_SRV, const._CLASS_IN, 1, 1, 1, 1, "a", created=1.0)
    record2 = r.DNSService("a", const._TYPE_SRV, const._CLASS_IN, 1, 1, 1, 1, "a", created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    assert next(iter(cache.async_entries_with_server("a"))) is record2


def test_async_get_returns_newest_record():
    cache = r.DNSCache()
    record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=1.0)
    record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    assert cache.get(record2) is record2


def test_async_get_returns_newest_nsec_record():
    cache = r.DNSCache()
    record1 = r.DNSNsec("a", const._TYPE_NSEC, const._CLASS_IN, 1, "a", [], created=1.0)
    record2 = r.DNSNsec("a", const._TYPE_NSEC, const._CLASS_IN, 1, "a", [], created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    assert cache.get(record2) is record2


def test_get_by_details_returns_newest_record():
    cache = r.DNSCache()
    record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=1.0)
    record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    assert cache.get_by_details("a", const._TYPE_A, const._CLASS_IN) is record2


def test_get_all_by_details_returns_newest_record():
    cache = r.DNSCache()
    record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=1.0)
    record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    records = cache.get_all_by_details("a", const._TYPE_A, const._CLASS_IN)
    assert len(records) == 1
    assert records[0] is record2


def test_async_get_all_by_details_returns_newest_record():
    cache = r.DNSCache()
    record1 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=1.0)
    record2 = r.DNSAddress("a", const._TYPE_A, const._CLASS_IN, 1, b"a", created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    records = cache.async_all_by_details("a", const._TYPE_A, const._CLASS_IN)
    assert len(records) == 1
    assert records[0] is record2


def test_async_get_unique_returns_newest_record():
    cache = r.DNSCache()
    record1 = r.DNSPointer("a", const._TYPE_PTR, const._CLASS_IN, 1, "a", created=1.0)
    record2 = r.DNSPointer("a", const._TYPE_PTR, const._CLASS_IN, 1, "a", created=2.0)
    cache.async_add_records([record1])
    cache.async_add_records([record2])
    record = cache.async_get_unique(record1)
    assert record is record2
    record = cache.async_get_unique(record2)
    assert record is record2


@pytest.mark.asyncio
async def test_cache_heap_cleanup() -> None:
    """Test that the heap gets cleaned up when there are many old expirations."""
    cache = r.DNSCache()
    # The heap should not be cleaned up when there are less than 100 expiration changes
    min_records_to_cleanup = 100
    now = r.current_time_millis()
    name = "heap.local."
    ttl_seconds = 100
    ttl_millis = ttl_seconds * 1000

    for i in range(min_records_to_cleanup):
        record = r.DNSAddress(name, const._TYPE_A, const._CLASS_IN, ttl_seconds, b"1", created=now + i)
        cache.async_add_records([record])

    assert len(cache._expire_heap) == min_records_to_cleanup
    assert len(cache.async_entries_with_name(name)) == 1

    # Now that we reached the minimum number of cookies to cleanup,
    # add one more cookie to trigger the cleanup
    record = r.DNSAddress(
        name, const._TYPE_A, const._CLASS_IN, ttl_seconds, b"1", created=now + min_records_to_cleanup
    )
    expected_expire_time = record.created + ttl_millis
    cache.async_add_records([record])
    assert len(cache.async_entries_with_name(name)) == 1
    entry = next(iter(cache.async_entries_with_name(name)))
    assert (entry.created + ttl_millis) == expected_expire_time
    assert entry is record

    # Verify that the heap has been cleaned up
    assert len(cache.async_entries_with_name(name)) == 1
    cache.async_expire(now)

    heap_copy = cache._expire_heap.copy()
    heapify(heap_copy)
    # Ensure heap order is maintained
    assert cache._expire_heap == heap_copy

    # The heap should have been cleaned up
    assert len(cache._expire_heap) == 1
    assert len(cache.async_entries_with_name(name)) == 1

    entry = next(iter(cache.async_entries_with_name(name)))
    assert entry is record

    assert (entry.created + ttl_millis) == expected_expire_time

    cache.async_expire(expected_expire_time)
    assert not cache.async_entries_with_name(name), cache._expire_heap


@pytest.mark.asyncio
async def test_cache_heap_multi_name_cleanup() -> None:
    """Test cleanup with multiple names."""
    cache = r.DNSCache()
    # The heap should not be cleaned up when there are less than 100 expiration changes
    min_records_to_cleanup = 100
    now = r.current_time_millis()
    name = "heap.local."
    name2 = "heap2.local."
    ttl_seconds = 100
    ttl_millis = ttl_seconds * 1000

    for i in range(min_records_to_cleanup):
        record = r.DNSAddress(name, const._TYPE_A, const._CLASS_IN, ttl_seconds, b"1", created=now + i)
        cache.async_add_records([record])
    expected_expire_time = record.created + ttl_millis

    for i in range(5):
        record = r.DNSAddress(
            name2, const._TYPE_A, const._CLASS_IN, ttl_seconds, bytes((i,)), created=now + i
        )
        cache.async_add_records([record])

    assert len(cache._expire_heap) == min_records_to_cleanup + 5
    assert len(cache.async_entries_with_name(name)) == 1
    assert len(cache.async_entries_with_name(name2)) == 5

    cache.async_expire(now)
    # The heap and expirations should have been cleaned up
    assert len(cache._expire_heap) == 1 + 5
    assert len(cache._expirations) == 1 + 5

    cache.async_expire(expected_expire_time)
    assert not cache.async_entries_with_name(name), cache._expire_heap


@pytest.mark.asyncio
async def test_cache_heap_pops_order() -> None:
    """Test cache heap is popped in order."""
    cache = r.DNSCache()
    # The heap should not be cleaned up when there are less than 100 expiration changes
    min_records_to_cleanup = 100
    now = r.current_time_millis()
    name = "heap.local."
    name2 = "heap2.local."
    ttl_seconds = 100

    for i in range(min_records_to_cleanup):
        record = r.DNSAddress(name, const._TYPE_A, const._CLASS_IN, ttl_seconds, b"1", created=now + i)
        cache.async_add_records([record])

    for i in range(5):
        record = r.DNSAddress(
            name2, const._TYPE_A, const._CLASS_IN, ttl_seconds, bytes((i,)), created=now + i
        )
        cache.async_add_records([record])

    assert len(cache._expire_heap) == min_records_to_cleanup + 5
    assert len(cache.async_entries_with_name(name)) == 1
    assert len(cache.async_entries_with_name(name2)) == 5

    start_ts = 0.0
    while cache._expire_heap:
        ts, _ = heappop(cache._expire_heap)
        assert ts >= start_ts
        start_ts = ts
