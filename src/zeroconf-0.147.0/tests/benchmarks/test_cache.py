from __future__ import annotations

from pytest_codspeed import BenchmarkFixture

from zeroconf import DNSCache, DNSPointer, current_time_millis
from zeroconf.const import _CLASS_IN, _TYPE_PTR


def test_add_expire_1000_records(benchmark: BenchmarkFixture) -> None:
    """Benchmark for DNSCache to expire 10000 records."""
    cache = DNSCache()
    now = current_time_millis()
    records = [
        DNSPointer(
            name=f"test{id}.local.",
            type_=_TYPE_PTR,
            class_=_CLASS_IN,
            ttl=60,
            alias=f"test{id}.local.",
            created=now + id,
        )
        for id in range(1000)
    ]

    @benchmark
    def _expire_records() -> None:
        cache.async_add_records(records)
        cache.async_expire(now + 100_000)


def test_expire_no_records_to_expire(benchmark: BenchmarkFixture) -> None:
    """Benchmark for DNSCache with 1000 records none to expire."""
    cache = DNSCache()
    now = current_time_millis()
    cache.async_add_records(
        DNSPointer(
            name=f"test{id}.local.",
            type_=_TYPE_PTR,
            class_=_CLASS_IN,
            ttl=60,
            alias=f"test{id}.local.",
            created=now + id,
        )
        for id in range(1000)
    )
    cache.async_expire(now)

    @benchmark
    def _expire_records() -> None:
        cache.async_expire(now)
