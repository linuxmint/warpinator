#!/usr/bin/env python


"""Unit tests for zeroconf._services.types."""

import logging
import os
import socket
import sys
import unittest

import zeroconf as r
from zeroconf import ServiceInfo, Zeroconf, ZeroconfServiceTypes

from .. import _clear_cache, has_working_ipv6

log = logging.getLogger('zeroconf')
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


def test_integration_with_listener(disable_duplicate_packet_suppression):
    type_ = "_test-listen-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    zeroconf_registrar = Zeroconf(interfaces=['127.0.0.1'])
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )
    zeroconf_registrar.registry.async_add(info)
    try:
        service_types = ZeroconfServiceTypes.find(interfaces=['127.0.0.1'], timeout=2)
        assert type_ in service_types
        _clear_cache(zeroconf_registrar)
        service_types = ZeroconfServiceTypes.find(zc=zeroconf_registrar, timeout=2)
        assert type_ in service_types

    finally:
        zeroconf_registrar.close()


@unittest.skipIf(not has_working_ipv6(), 'Requires IPv6')
@unittest.skipIf(os.environ.get('SKIP_IPV6'), 'IPv6 tests disabled')
def test_integration_with_listener_v6_records(disable_duplicate_packet_suppression):
    type_ = "_test-listenv6rec-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    addr = "2606:2800:220:1:248:1893:25c8:1946"  # example.com

    zeroconf_registrar = Zeroconf(interfaces=['127.0.0.1'])
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_pton(socket.AF_INET6, addr)],
    )
    zeroconf_registrar.registry.async_add(info)
    try:
        service_types = ZeroconfServiceTypes.find(interfaces=['127.0.0.1'], timeout=2)
        assert type_ in service_types
        _clear_cache(zeroconf_registrar)
        service_types = ZeroconfServiceTypes.find(zc=zeroconf_registrar, timeout=2)
        assert type_ in service_types

    finally:
        zeroconf_registrar.close()


@unittest.skipIf(not has_working_ipv6() or sys.platform == 'win32', 'Requires IPv6')
@unittest.skipIf(os.environ.get('SKIP_IPV6'), 'IPv6 tests disabled')
def test_integration_with_listener_ipv6(disable_duplicate_packet_suppression):
    type_ = "_test-listenv6ip-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    addr = "2606:2800:220:1:248:1893:25c8:1946"  # example.com

    zeroconf_registrar = Zeroconf(ip_version=r.IPVersion.V6Only)
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_pton(socket.AF_INET6, addr)],
    )
    zeroconf_registrar.registry.async_add(info)
    try:
        service_types = ZeroconfServiceTypes.find(ip_version=r.IPVersion.V6Only, timeout=2)
        assert type_ in service_types
        _clear_cache(zeroconf_registrar)
        service_types = ZeroconfServiceTypes.find(zc=zeroconf_registrar, timeout=2)
        assert type_ in service_types

    finally:
        zeroconf_registrar.close()


def test_integration_with_subtype_and_listener(disable_duplicate_packet_suppression):
    subtype_ = "_subtype._sub"
    type_ = "_listen._tcp.local."
    name = "xxxyyy"
    # Note: discovery returns only DNS-SD type not subtype
    discovery_type = f"{subtype_}.{type_}"
    registration_name = f"{name}.{type_}"

    zeroconf_registrar = Zeroconf(interfaces=['127.0.0.1'])
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        discovery_type,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )
    zeroconf_registrar.registry.async_add(info)
    try:
        service_types = ZeroconfServiceTypes.find(interfaces=['127.0.0.1'], timeout=2)
        assert discovery_type in service_types
        _clear_cache(zeroconf_registrar)
        service_types = ZeroconfServiceTypes.find(zc=zeroconf_registrar, timeout=2)
        assert discovery_type in service_types

    finally:
        zeroconf_registrar.close()
