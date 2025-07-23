"""Unit tests for zeroconf._services."""

from __future__ import annotations

import logging
import os
import socket
import time
import unittest
from threading import Event
from typing import Any

import pytest

import zeroconf as r
from zeroconf import Zeroconf
from zeroconf._services.info import ServiceInfo

from . import _clear_cache, has_working_ipv6

log = logging.getLogger("zeroconf")
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


class ListenerTest(unittest.TestCase):
    def test_integration_with_listener_class(self):
        sub_service_added = Event()
        service_added = Event()
        service_removed = Event()
        sub_service_updated = Event()
        duplicate_service_added = Event()

        subtype_name = "_printer"
        type_ = "_http._tcp.local."
        subtype = subtype_name + "._sub." + type_
        name = "UPPERxxxyyyæøå"
        registration_name = f"{name}.{subtype}"

        class MyListener(r.ServiceListener):
            def add_service(self, zeroconf, type, name):
                zeroconf.get_service_info(type, name)
                service_added.set()

            def remove_service(self, zeroconf, type, name):
                service_removed.set()

            def update_service(self, zeroconf, type, name):
                pass

        class DuplicateListener(r.ServiceListener):
            def add_service(self, zeroconf, type, name):
                duplicate_service_added.set()

            def remove_service(self, zeroconf, type, name):
                pass

            def update_service(self, zeroconf, type, name):
                pass

        class MySubListener(r.ServiceListener):
            def add_service(self, zeroconf, type, name):
                sub_service_added.set()

            def remove_service(self, zeroconf, type, name):
                pass

            def update_service(self, zeroconf, type, name):
                sub_service_updated.set()

        listener = MyListener()
        zeroconf_browser = Zeroconf(interfaces=["127.0.0.1"])
        zeroconf_browser.add_service_listener(type_, listener)

        properties = {
            "prop_none": None,
            "prop_string": b"a_prop",
            "prop_float": 1.0,
            "prop_blank": b"a blanked string",
            "prop_true": 1,
            "prop_false": 0,
        }

        zeroconf_registrar = Zeroconf(interfaces=["127.0.0.1"])
        desc: dict[str, Any] = {"path": "/~paulsm/"}
        desc.update(properties)
        addresses = [socket.inet_aton("10.0.1.2")]
        if has_working_ipv6() and not os.environ.get("SKIP_IPV6"):
            addresses.append(socket.inet_pton(socket.AF_INET6, "6001:db8::1"))
            addresses.append(socket.inet_pton(socket.AF_INET6, "2001:db8::1"))
        info_service = ServiceInfo(
            subtype,
            registration_name,
            port=80,
            properties=desc,
            server="ash-2.local.",
            addresses=addresses,
        )
        zeroconf_registrar.register_service(info_service)

        try:
            service_added.wait(1)
            assert service_added.is_set()

            # short pause to allow multicast timers to expire
            time.sleep(3)

            zeroconf_browser.add_service_listener(type_, DuplicateListener())
            duplicate_service_added.wait(
                1
            )  # Ensure a listener for the same type calls back right away from cache

            # clear the answer cache to force query
            _clear_cache(zeroconf_browser)

            cached_info = ServiceInfo(type_, registration_name)
            cached_info.load_from_cache(zeroconf_browser)
            assert cached_info.properties == {}

            # get service info without answer cache
            info = zeroconf_browser.get_service_info(type_, registration_name)
            assert info is not None
            assert info.properties[b"prop_none"] is None
            assert info.properties[b"prop_string"] == properties["prop_string"]
            assert info.properties[b"prop_float"] == b"1.0"
            assert info.properties[b"prop_blank"] == properties["prop_blank"]
            assert info.properties[b"prop_true"] == b"1"
            assert info.properties[b"prop_false"] == b"0"

            assert info.decoded_properties["prop_none"] is None
            assert info.decoded_properties["prop_string"] == b"a_prop".decode("utf-8")
            assert info.decoded_properties["prop_float"] == "1.0"
            assert info.decoded_properties["prop_blank"] == b"a blanked string".decode("utf-8")
            assert info.decoded_properties["prop_true"] == "1"
            assert info.decoded_properties["prop_false"] == "0"

            assert info.addresses == addresses[:1]  # no V6 by default
            assert set(info.addresses_by_version(r.IPVersion.All)) == set(addresses)

            cached_info = ServiceInfo(type_, registration_name)
            cached_info.load_from_cache(zeroconf_browser)
            assert cached_info.properties is not None

            # Populate the cache
            zeroconf_browser.get_service_info(subtype, registration_name)

            # get service info with only the cache
            cached_info = ServiceInfo(subtype, registration_name)
            cached_info.load_from_cache(zeroconf_browser)
            assert cached_info.properties is not None
            assert cached_info.properties[b"prop_float"] == b"1.0"

            # get service info with only the cache with the lowercase name
            cached_info = ServiceInfo(subtype, registration_name.lower())
            cached_info.load_from_cache(zeroconf_browser)
            # Ensure uppercase output is preserved
            assert cached_info.name == registration_name
            assert cached_info.key == registration_name.lower()
            assert cached_info.properties is not None
            assert cached_info.properties[b"prop_float"] == b"1.0"

            info = zeroconf_browser.get_service_info(subtype, registration_name)
            assert info is not None
            assert info.properties is not None
            assert info.properties[b"prop_none"] is None

            cached_info = ServiceInfo(subtype, registration_name.lower())
            cached_info.load_from_cache(zeroconf_browser)
            assert cached_info.properties is not None
            assert cached_info.properties[b"prop_none"] is None

            # test TXT record update
            sublistener = MySubListener()

            zeroconf_browser.add_service_listener(subtype, sublistener)

            properties["prop_blank"] = b"an updated string"
            desc.update(properties)
            info_service = ServiceInfo(
                subtype,
                registration_name,
                80,
                0,
                0,
                desc,
                "ash-2.local.",
                addresses=[socket.inet_aton("10.0.1.2")],
            )
            zeroconf_registrar.update_service(info_service)

            sub_service_added.wait(1)  # we cleared the cache above
            assert sub_service_added.is_set()

            info = zeroconf_browser.get_service_info(type_, registration_name)
            assert info is not None
            assert info.properties[b"prop_blank"] == properties["prop_blank"]
            assert info.decoded_properties["prop_blank"] == b"an updated string".decode("utf-8")

            cached_info = ServiceInfo(subtype, registration_name)
            cached_info.load_from_cache(zeroconf_browser)
            assert cached_info.properties is not None
            assert cached_info.properties[b"prop_blank"] == properties["prop_blank"]
            assert cached_info.decoded_properties["prop_blank"] == b"an updated string".decode("utf-8")

            zeroconf_registrar.unregister_service(info_service)
            service_removed.wait(1)
            assert service_removed.is_set()

        finally:
            zeroconf_registrar.close()
            zeroconf_browser.remove_service_listener(listener)
            zeroconf_browser.close()


def test_servicelisteners_raise_not_implemented():
    """Verify service listeners raise when one of the methods is not implemented."""

    class MyPartialListener(r.ServiceListener):
        """A listener that does not implement anything."""

    zc = r.Zeroconf(interfaces=["127.0.0.1"])

    with pytest.raises(NotImplementedError):
        MyPartialListener().add_service(
            zc, "_tivo-videostream._tcp.local.", "Tivo1._tivo-videostream._tcp.local."
        )
    with pytest.raises(NotImplementedError):
        MyPartialListener().remove_service(
            zc, "_tivo-videostream._tcp.local.", "Tivo1._tivo-videostream._tcp.local."
        )
    with pytest.raises(NotImplementedError):
        MyPartialListener().update_service(
            zc, "_tivo-videostream._tcp.local.", "Tivo1._tivo-videostream._tcp.local."
        )

    zc.close()


def test_signal_registration_interface():
    """Test adding and removing from the SignalRegistrationInterface."""

    interface = r.SignalRegistrationInterface([])

    def dummy():
        pass

    interface.register_handler(dummy)
    interface.unregister_handler(dummy)

    with pytest.raises(ValueError):
        interface.unregister_handler(dummy)
