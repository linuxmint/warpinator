"""Unit tests for zeroconf.py"""

from __future__ import annotations

import logging
import socket
import time
import unittest.mock
from unittest.mock import patch

import zeroconf as r
from zeroconf import ServiceInfo, Zeroconf, const

from . import _inject_responses

log = logging.getLogger("zeroconf")
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


class Names(unittest.TestCase):
    def test_long_name(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        question = r.DNSQuestion(
            "this.is.a.very.long.name.with.lots.of.parts.in.it.local.",
            const._TYPE_SRV,
            const._CLASS_IN,
        )
        generated.add_question(question)
        r.DNSIncoming(generated.packets()[0])

    def test_exceedingly_long_name(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        name = f"{'part.' * 1000}local."
        question = r.DNSQuestion(name, const._TYPE_SRV, const._CLASS_IN)
        generated.add_question(question)
        r.DNSIncoming(generated.packets()[0])

    def test_extra_exceedingly_long_name(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        name = f"{'part.' * 4000}local."
        question = r.DNSQuestion(name, const._TYPE_SRV, const._CLASS_IN)
        generated.add_question(question)
        r.DNSIncoming(generated.packets()[0])

    def test_exceedingly_long_name_part(self):
        name = f"{'a' * 1000}.local."
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        question = r.DNSQuestion(name, const._TYPE_SRV, const._CLASS_IN)
        generated.add_question(question)
        self.assertRaises(r.NamePartTooLongException, generated.packets)

    def test_same_name(self):
        name = "paired.local."
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        question = r.DNSQuestion(name, const._TYPE_SRV, const._CLASS_IN)
        generated.add_question(question)
        generated.add_question(question)
        r.DNSIncoming(generated.packets()[0])

    def test_verify_name_change_with_lots_of_names(self):
        # instantiate a zeroconf instance
        zc = Zeroconf(interfaces=["127.0.0.1"])

        # create a bunch of servers
        type_ = "_my-service._tcp.local."
        name = "a wonderful service"
        server_count = 300
        self.generate_many_hosts(zc, type_, name, server_count)

        # verify that name changing works
        self.verify_name_change(zc, type_, name, server_count)

        zc.close()

    def test_large_packet_exception_log_handling(self):
        """Verify we downgrade debug after warning."""

        # instantiate a zeroconf instance
        zc = Zeroconf(interfaces=["127.0.0.1"])

        with (
            patch("zeroconf._logger.log.warning") as mocked_log_warn,
            patch("zeroconf._logger.log.debug") as mocked_log_debug,
        ):
            # now that we have a long packet in our possession, let's verify the
            # exception handling.
            out = r.DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA)
            out.data.append(b"\0" * 10000)

            # mock the zeroconf logger and check for the correct logging backoff
            call_counts = mocked_log_warn.call_count, mocked_log_debug.call_count
            # try to send an oversized packet
            zc.send(out)
            assert mocked_log_warn.call_count == call_counts[0]
            zc.send(out)
            assert mocked_log_warn.call_count == call_counts[0]

            # mock the zeroconf logger and check for the correct logging backoff
            call_counts = mocked_log_warn.call_count, mocked_log_debug.call_count
            # force receive on oversized packet
            zc.send(out, const._MDNS_ADDR, const._MDNS_PORT)
            zc.send(out, const._MDNS_ADDR, const._MDNS_PORT)
            time.sleep(0.3)
            r.log.debug(
                "warn %d debug %d was %s",
                mocked_log_warn.call_count,
                mocked_log_debug.call_count,
                call_counts,
            )
            assert mocked_log_debug.call_count > call_counts[0]

        # close our zeroconf which will close the sockets
        zc.close()

    def verify_name_change(self, zc, type_, name, number_hosts):
        desc = {"path": "/~paulsm/"}
        info_service = ServiceInfo(
            type_,
            f"{name}.{type_}",
            80,
            0,
            0,
            desc,
            "ash-2.local.",
            addresses=[socket.inet_aton("10.0.1.2")],
        )

        # verify name conflict
        self.assertRaises(r.NonUniqueNameException, zc.register_service, info_service)

        # verify no name conflict https://tools.ietf.org/html/rfc6762#section-6.6
        zc.register_service(info_service, cooperating_responders=True)

        # Create a new object since allow_name_change will mutate the
        # original object and then we will have the wrong service
        # in the registry
        info_service2 = ServiceInfo(
            type_,
            f"{name}.{type_}",
            80,
            0,
            0,
            desc,
            "ash-2.local.",
            addresses=[socket.inet_aton("10.0.1.2")],
        )
        zc.register_service(info_service2, allow_name_change=True)
        assert info_service2.name.split(".")[0] == f"{name}-{number_hosts + 1}"

    def generate_many_hosts(self, zc, type_, name, number_hosts):
        block_size = 25
        number_hosts = int((number_hosts - 1) / block_size + 1) * block_size
        out = r.DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA)
        for i in range(1, number_hosts + 1):
            next_name = name if i == 1 else f"{name}-{i}"
            self.generate_host(out, next_name, type_)

        _inject_responses(zc, [r.DNSIncoming(packet) for packet in out.packets()])

    @staticmethod
    def generate_host(out, host_name, type_):
        name = ".".join((host_name, type_))
        out.add_answer_at_time(
            r.DNSPointer(type_, const._TYPE_PTR, const._CLASS_IN, const._DNS_OTHER_TTL, name),
            0,
        )
        out.add_answer_at_time(
            r.DNSService(
                type_,
                const._TYPE_SRV,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                0,
                0,
                80,
                name,
            ),
            0,
        )
