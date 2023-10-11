#!/usr/bin/env python


""" Unit tests for zeroconf._cache. """


import logging
import unittest
import unittest.mock

import zeroconf as r
from zeroconf import const

log = logging.getLogger('zeroconf')
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
        record1 = r.DNSAddress('a', const._TYPE_SOA, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_SOA, const._CLASS_IN, 1, b'b')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        entry = r.DNSEntry('a', const._TYPE_SOA, const._CLASS_IN)
        cached_record = cache.get(entry)
        assert cached_record == record2

    def test_adding_same_record_to_cache_different_ttls_with_get(self):
        """We should always get back the last entry we added if there are different TTLs.

        This ensures we only have one source of truth for TTLs as a record cannot
        be both expired and not expired.
        """
        record1 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 10, b'a')
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
        record1 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 10, b'a')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        cached_records = cache.get_all_by_details('a', const._TYPE_A, const._CLASS_IN)
        assert cached_records == [record2]

    def test_cache_empty_does_not_leak_memory_by_leaving_empty_list(self):
        record1 = r.DNSAddress('a', const._TYPE_SOA, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_SOA, const._CLASS_IN, 1, b'b')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert 'a' in cache.cache
        cache.async_remove_records([record1, record2])
        assert 'a' not in cache.cache

    def test_cache_empty_multiple_calls(self):
        record1 = r.DNSAddress('a', const._TYPE_SOA, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_SOA, const._CLASS_IN, 1, b'b')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert 'a' in cache.cache
        cache.async_remove_records([record1, record2])
        assert 'a' not in cache.cache


class TestDNSAsyncCacheAPI(unittest.TestCase):
    def test_async_get_unique(self):
        record1 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'b')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.async_get_unique(record1) == record1
        assert cache.async_get_unique(record2) == record2

    def test_async_all_by_details(self):
        record1 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'b')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.async_all_by_details('a', const._TYPE_A, const._CLASS_IN)) == {record1, record2}

    def test_async_entries_with_server(self):
        record1 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 85, 'ab'
        )
        record2 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 80, 'ab'
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.async_entries_with_server('ab')) == {record1, record2}
        assert set(cache.async_entries_with_server('AB')) == {record1, record2}

    def test_async_entries_with_name(self):
        record1 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 85, 'ab'
        )
        record2 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 80, 'ab'
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.async_entries_with_name('irrelevant')) == {record1, record2}
        assert set(cache.async_entries_with_name('Irrelevant')) == {record1, record2}


# These functions have been seen in other projects so
# we try to maintain a stable API for all the threadsafe getters
class TestDNSCacheAPI(unittest.TestCase):
    def test_get(self):
        record1 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'b')
        record3 = r.DNSAddress('a', const._TYPE_AAAA, const._CLASS_IN, 1, b'ipv6')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2, record3])
        assert cache.get(record1) == record1
        assert cache.get(record2) == record2
        assert cache.get(r.DNSEntry('a', const._TYPE_A, const._CLASS_IN)) == record2
        assert cache.get(r.DNSEntry('a', const._TYPE_AAAA, const._CLASS_IN)) == record3
        assert cache.get(r.DNSEntry('notthere', const._TYPE_A, const._CLASS_IN)) is None

    def test_get_by_details(self):
        record1 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'b')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.get_by_details('a', const._TYPE_A, const._CLASS_IN) == record2

    def test_get_all_by_details(self):
        record1 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'a')
        record2 = r.DNSAddress('a', const._TYPE_A, const._CLASS_IN, 1, b'b')
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.get_all_by_details('a', const._TYPE_A, const._CLASS_IN)) == {record1, record2}

    def test_entries_with_server(self):
        record1 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 85, 'ab'
        )
        record2 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 80, 'ab'
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.entries_with_server('ab')) == {record1, record2}
        assert set(cache.entries_with_server('AB')) == {record1, record2}

    def test_entries_with_name(self):
        record1 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 85, 'ab'
        )
        record2 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 80, 'ab'
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert set(cache.entries_with_name('irrelevant')) == {record1, record2}
        assert set(cache.entries_with_name('Irrelevant')) == {record1, record2}

    def test_current_entry_with_name_and_alias(self):
        record1 = r.DNSPointer(
            'irrelevant', const._TYPE_PTR, const._CLASS_IN, const._DNS_OTHER_TTL, 'x.irrelevant'
        )
        record2 = r.DNSPointer(
            'irrelevant', const._TYPE_PTR, const._CLASS_IN, const._DNS_OTHER_TTL, 'y.irrelevant'
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.current_entry_with_name_and_alias('irrelevant', 'x.irrelevant') == record1

    def test_name(self):
        record1 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 85, 'ab'
        )
        record2 = r.DNSService(
            'irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, 0, 0, 80, 'ab'
        )
        cache = r.DNSCache()
        cache.async_add_records([record1, record2])
        assert cache.names() == ['irrelevant']
