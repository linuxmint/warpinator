"""Unit tests for zeroconf._utils.ipaddress."""

from __future__ import annotations

from zeroconf import const
from zeroconf._dns import DNSAddress
from zeroconf._utils import ipaddress


def test_cached_ip_addresses_wrapper():
    """Test the cached_ip_addresses_wrapper."""
    assert ipaddress.cached_ip_addresses("") is None
    assert ipaddress.cached_ip_addresses("foo") is None
    assert (
        str(ipaddress.cached_ip_addresses(b"&\x06(\x00\x02 \x00\x01\x02H\x18\x93%\xc8\x19F"))
        == "2606:2800:220:1:248:1893:25c8:1946"
    )
    loop_back_ipv6 = ipaddress.cached_ip_addresses("::1")
    assert loop_back_ipv6 == ipaddress.IPv6Address("::1")
    assert loop_back_ipv6.is_loopback is True

    assert hash(loop_back_ipv6) == hash(ipaddress.IPv6Address("::1"))

    loop_back_ipv4 = ipaddress.cached_ip_addresses("127.0.0.1")
    assert loop_back_ipv4 == ipaddress.IPv4Address("127.0.0.1")
    assert loop_back_ipv4.is_loopback is True

    assert hash(loop_back_ipv4) == hash(ipaddress.IPv4Address("127.0.0.1"))

    ipv4 = ipaddress.cached_ip_addresses("169.254.0.0")
    assert ipv4 is not None
    assert ipv4.is_link_local is True
    assert ipv4.is_unspecified is False

    ipv4 = ipaddress.cached_ip_addresses("0.0.0.0")
    assert ipv4 is not None
    assert ipv4.is_link_local is False
    assert ipv4.is_unspecified is True

    ipv6 = ipaddress.cached_ip_addresses("fe80::1")
    assert ipv6 is not None
    assert ipv6.is_link_local is True
    assert ipv6.is_unspecified is False

    ipv6 = ipaddress.cached_ip_addresses("0:0:0:0:0:0:0:0")
    assert ipv6 is not None
    assert ipv6.is_link_local is False
    assert ipv6.is_unspecified is True


def test_get_ip_address_object_from_record():
    """Test the get_ip_address_object_from_record."""
    # not link local
    packed = b"&\x06(\x00\x02 \x00\x01\x02H\x18\x93%\xc8\x19F"
    record = DNSAddress(
        "domain.local",
        const._TYPE_AAAA,
        const._CLASS_IN | const._CLASS_UNIQUE,
        1,
        packed,
        scope_id=3,
    )
    assert record.scope_id == 3
    assert ipaddress.get_ip_address_object_from_record(record) == ipaddress.IPv6Address(
        "2606:2800:220:1:248:1893:25c8:1946"
    )

    # link local
    packed = b"\xfe\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
    record = DNSAddress(
        "domain.local",
        const._TYPE_AAAA,
        const._CLASS_IN | const._CLASS_UNIQUE,
        1,
        packed,
        scope_id=3,
    )
    assert record.scope_id == 3
    assert ipaddress.get_ip_address_object_from_record(record) == ipaddress.IPv6Address("fe80::1%3")
    record = DNSAddress(
        "domain.local",
        const._TYPE_AAAA,
        const._CLASS_IN | const._CLASS_UNIQUE,
        1,
        packed,
    )
    assert record.scope_id is None
    assert ipaddress.get_ip_address_object_from_record(record) == ipaddress.IPv6Address("fe80::1")
    record = DNSAddress(
        "domain.local",
        const._TYPE_A,
        const._CLASS_IN | const._CLASS_UNIQUE,
        1,
        packed,
        scope_id=0,
    )
    assert record.scope_id == 0
    # Ensure scope_id of 0 is not appended to the address
    assert ipaddress.get_ip_address_object_from_record(record) == ipaddress.IPv6Address("fe80::1")
