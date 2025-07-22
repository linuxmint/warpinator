"""Unit tests for zeroconf._exceptions"""

from __future__ import annotations

import logging
import unittest.mock

import zeroconf as r
from zeroconf import ServiceInfo, Zeroconf

log = logging.getLogger("zeroconf")
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


class Exceptions(unittest.TestCase):
    browser = None  # type: Zeroconf

    @classmethod
    def setUpClass(cls):
        cls.browser = Zeroconf(interfaces=["127.0.0.1"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        del cls.browser

    def test_bad_service_info_name(self):
        self.assertRaises(r.BadTypeInNameException, self.browser.get_service_info, "type", "type_not")

    def test_bad_service_names(self):
        bad_names_to_try = (
            "",
            "local",
            "_tcp.local.",
            "_udp.local.",
            "._udp.local.",
            "_@._tcp.local.",
            "_A@._tcp.local.",
            "_x--x._tcp.local.",
            "_-x._udp.local.",
            "_x-._tcp.local.",
            "_22._udp.local.",
            "_2-2._tcp.local.",
            "\x00._x._udp.local.",
        )
        for name in bad_names_to_try:
            self.assertRaises(
                r.BadTypeInNameException,
                self.browser.get_service_info,
                name,
                "x." + name,
            )

    def test_bad_local_names_for_get_service_info(self):
        bad_names_to_try = (
            "homekitdev._nothttp._tcp.local.",
            "homekitdev._http._udp.local.",
        )
        for name in bad_names_to_try:
            self.assertRaises(
                r.BadTypeInNameException,
                self.browser.get_service_info,
                "_http._tcp.local.",
                name,
            )

    def test_good_instance_names(self):
        assert r.service_type_name(".._x._tcp.local.") == "_x._tcp.local."
        assert r.service_type_name("x.y._http._tcp.local.") == "_http._tcp.local."
        assert r.service_type_name("1.2.3._mqtt._tcp.local.") == "_mqtt._tcp.local."
        assert r.service_type_name("x.sub._http._tcp.local.") == "_http._tcp.local."
        assert (
            r.service_type_name("6d86f882b90facee9170ad3439d72a4d6ee9f511._zget._http._tcp.local.")
            == "_http._tcp.local."
        )

    def test_good_instance_names_without_protocol(self):
        good_names_to_try = (
            "Rachio-C73233.local.",
            "YeelightColorBulb-3AFD.local.",
            "YeelightTunableBulb-7220.local.",
            "AlexanderHomeAssistant 74651D.local.",
            "iSmartGate-152.local.",
            "MyQ-FGA.local.",
            "lutron-02c4392a.local.",
            "WICED-hap-3E2734.local.",
            "MyHost.local.",
            "MyHost.sub.local.",
        )
        for name in good_names_to_try:
            assert r.service_type_name(name, strict=False) == "local."

        for name in good_names_to_try:
            # Raises without strict=False
            self.assertRaises(r.BadTypeInNameException, r.service_type_name, name)

    def test_bad_types(self):
        bad_names_to_try = (
            "._x._tcp.local.",
            "a" * 64 + "._sub._http._tcp.local.",
            "a" * 62 + "â._sub._http._tcp.local.",
        )
        for name in bad_names_to_try:
            self.assertRaises(r.BadTypeInNameException, r.service_type_name, name)

    def test_bad_sub_types(self):
        bad_names_to_try = (
            "_sub._http._tcp.local.",
            "._sub._http._tcp.local.",
            "\x7f._sub._http._tcp.local.",
            "\x1f._sub._http._tcp.local.",
        )
        for name in bad_names_to_try:
            self.assertRaises(r.BadTypeInNameException, r.service_type_name, name)

    def test_good_service_names(self):
        good_names_to_try = (
            ("_x._tcp.local.", "_x._tcp.local."),
            ("_x._udp.local.", "_x._udp.local."),
            ("_12345-67890-abc._udp.local.", "_12345-67890-abc._udp.local."),
            ("x._sub._http._tcp.local.", "_http._tcp.local."),
            ("a" * 63 + "._sub._http._tcp.local.", "_http._tcp.local."),
            ("a" * 61 + "â._sub._http._tcp.local.", "_http._tcp.local."),
        )

        for name, result in good_names_to_try:
            assert r.service_type_name(name) == result

        assert r.service_type_name("_one_two._tcp.local.", strict=False) == "_one_two._tcp.local."

    def test_invalid_addresses(self):
        type_ = "_test-srvc-type._tcp.local."
        name = "xxxyyy"
        registration_name = f"{name}.{type_}"

        bad = (b"127.0.0.1", b"::1")
        for addr in bad:
            self.assertRaisesRegex(
                TypeError,
                "Addresses must either ",
                ServiceInfo,
                type_,
                registration_name,
                port=80,
                addresses=[addr],
            )
