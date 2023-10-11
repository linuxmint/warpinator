#!/usr/bin/env python


""" Unit tests for zeroconf._listener """

import logging
import unittest
import unittest.mock
from typing import Tuple, Union
from unittest.mock import MagicMock, patch

import zeroconf as r
from zeroconf import Zeroconf, _engine, _listener, const, current_time_millis
from zeroconf._protocol import outgoing
from zeroconf._protocol.incoming import DNSIncoming

from . import QuestionHistoryWithoutSuppression

log = logging.getLogger('zeroconf')
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


def test_guard_against_oversized_packets():
    """Ensure we do not process oversized packets.

    These packets can quickly overwhelm the system.
    """
    zc = Zeroconf(interfaces=['127.0.0.1'])

    generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)

    for i in range(5000):
        generated.add_answer_at_time(
            r.DNSText(
                "packet{i}.local.",
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                500,
                b'path=/~paulsm/',
            ),
            0,
        )

    try:
        # We are patching to generate an oversized packet
        with patch.object(outgoing, "_MAX_MSG_ABSOLUTE", 100000), patch.object(
            outgoing, "_MAX_MSG_TYPICAL", 100000
        ):
            over_sized_packet = generated.packets()[0]
            assert len(over_sized_packet) > const._MAX_MSG_ABSOLUTE
    except AttributeError:
        # cannot patch with cython
        zc.close()
        return

    generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
    okpacket_record = r.DNSText(
        "okpacket.local.",
        const._TYPE_TXT,
        const._CLASS_IN | const._CLASS_UNIQUE,
        500,
        b'path=/~paulsm/',
    )

    generated.add_answer_at_time(
        okpacket_record,
        0,
    )
    ok_packet = generated.packets()[0]

    # We cannot test though the network interface as some operating systems
    # will guard against the oversized packet and we won't see it.
    listener = _listener.AsyncListener(zc)
    listener.transport = unittest.mock.MagicMock()

    listener.datagram_received(ok_packet, ('127.0.0.1', const._MDNS_PORT))
    assert zc.cache.async_get_unique(okpacket_record) is not None

    listener.datagram_received(over_sized_packet, ('127.0.0.1', const._MDNS_PORT))
    assert (
        zc.cache.async_get_unique(
            r.DNSText(
                "packet0.local.",
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                500,
                b'path=/~paulsm/',
            )
        )
        is None
    )

    logging.getLogger('zeroconf').setLevel(logging.INFO)

    listener.datagram_received(over_sized_packet, ('::1', const._MDNS_PORT, 1, 1))
    assert (
        zc.cache.async_get_unique(
            r.DNSText(
                "packet0.local.",
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                500,
                b'path=/~paulsm/',
            )
        )
        is None
    )

    zc.close()


def test_guard_against_duplicate_packets():
    """Ensure we do not process duplicate packets.
    These packets can quickly overwhelm the system.
    """
    zc = Zeroconf(interfaces=['127.0.0.1'])
    zc.question_history = QuestionHistoryWithoutSuppression()

    class SubListener(_listener.AsyncListener):
        def handle_query_or_defer(
            self,
            msg: DNSIncoming,
            addr: str,
            port: int,
            transport: _engine._WrappedTransport,
            v6_flow_scope: Union[Tuple[()], Tuple[int, int]] = (),
        ) -> None:
            """Handle a query or defer it for later processing."""
            super().handle_query_or_defer(msg, addr, port, transport, v6_flow_scope)

    listener = SubListener(zc)
    listener.transport = MagicMock()

    query = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    question = r.DNSQuestion("x._http._tcp.local.", const._TYPE_PTR, const._CLASS_IN)
    query.add_question(question)
    packet_with_qm_question = query.packets()[0]

    query3 = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    question3 = r.DNSQuestion("x._ay._tcp.local.", const._TYPE_PTR, const._CLASS_IN)
    query3.add_question(question3)
    packet_with_qm_question2 = query3.packets()[0]

    query2 = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    question2 = r.DNSQuestion("x._http._tcp.local.", const._TYPE_PTR, const._CLASS_IN)
    question2.unicast = True
    query2.add_question(question2)
    packet_with_qu_question = query2.packets()[0]

    addrs = ("1.2.3.4", 43)

    with patch.object(_listener, "current_time_millis") as _current_time_millis, patch.object(
        listener, "handle_query_or_defer"
    ) as _handle_query_or_defer:
        start_time = current_time_millis()

        _current_time_millis.return_value = start_time
        listener.datagram_received(packet_with_qm_question, addrs)
        _handle_query_or_defer.assert_called_once()
        _handle_query_or_defer.reset_mock()

        # Now call with the same packet again and handle_query_or_defer should not fire
        listener.datagram_received(packet_with_qm_question, addrs)
        _handle_query_or_defer.assert_not_called()
        _handle_query_or_defer.reset_mock()

        # Now walk time forward 1000 seconds
        _current_time_millis.return_value = start_time + 1000
        # Now call with the same packet again and handle_query_or_defer should fire
        listener.datagram_received(packet_with_qm_question, addrs)
        _handle_query_or_defer.assert_called_once()
        _handle_query_or_defer.reset_mock()

        # Now call with the different packet and handle_query_or_defer should fire
        listener.datagram_received(packet_with_qm_question2, addrs)
        _handle_query_or_defer.assert_called_once()
        _handle_query_or_defer.reset_mock()

        # Now call with the different packet and handle_query_or_defer should fire
        listener.datagram_received(packet_with_qm_question, addrs)
        _handle_query_or_defer.assert_called_once()
        _handle_query_or_defer.reset_mock()

        # Now call with the different packet with qu question and handle_query_or_defer should fire
        listener.datagram_received(packet_with_qu_question, addrs)
        _handle_query_or_defer.assert_called_once()
        _handle_query_or_defer.reset_mock()

        # Now call again with the same packet that has a qu question and handle_query_or_defer should fire
        listener.datagram_received(packet_with_qu_question, addrs)
        _handle_query_or_defer.assert_called_once()
        _handle_query_or_defer.reset_mock()

        log.setLevel(logging.WARNING)

        # Call with the QM packet again
        listener.datagram_received(packet_with_qm_question, addrs)
        _handle_query_or_defer.assert_called_once()
        _handle_query_or_defer.reset_mock()

        # Now call with the same packet again and handle_query_or_defer should not fire
        listener.datagram_received(packet_with_qm_question, addrs)
        _handle_query_or_defer.assert_not_called()
        _handle_query_or_defer.reset_mock()

        # Now call with garbage
        listener.datagram_received(b'garbage', addrs)
        _handle_query_or_defer.assert_not_called()
        _handle_query_or_defer.reset_mock()

    zc.close()
