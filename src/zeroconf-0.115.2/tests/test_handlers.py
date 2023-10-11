#!/usr/bin/env python


""" Unit tests for zeroconf._handlers """

import asyncio
import logging
import os
import socket
import time
import unittest
import unittest.mock
from typing import List, cast

import pytest

import zeroconf as r
from zeroconf import ServiceInfo, Zeroconf, const, current_time_millis
from zeroconf._handlers import multicast_outgoing_queue
from zeroconf._handlers.multicast_outgoing_queue import (
    MulticastOutgoingQueue,
    construct_outgoing_multicast_answers,
)
from zeroconf._utils.time import millis_to_seconds
from zeroconf.asyncio import AsyncZeroconf

from . import _clear_cache, _inject_response, has_working_ipv6

log = logging.getLogger('zeroconf')
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


class TestRegistrar(unittest.TestCase):
    def test_ttl(self):
        # instantiate a zeroconf instance
        zc = Zeroconf(interfaces=['127.0.0.1'])

        # service definition
        type_ = "_test-srvc-type._tcp.local."
        name = "xxxyyy"
        registration_name = f"{name}.{type_}"

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

        nbr_answers = nbr_additionals = nbr_authorities = 0

        def get_ttl(record_type):
            if expected_ttl is not None:
                return expected_ttl
            elif record_type in [const._TYPE_A, const._TYPE_SRV, const._TYPE_NSEC]:
                return const._DNS_HOST_TTL
            else:
                return const._DNS_OTHER_TTL

        def _process_outgoing_packet(out):
            """Sends an outgoing packet."""
            nonlocal nbr_answers, nbr_additionals, nbr_authorities

            for answer, time_ in out.answers:
                nbr_answers += 1
                assert answer.ttl == get_ttl(answer.type)
            for answer in out.additionals:
                nbr_additionals += 1
                assert answer.ttl == get_ttl(answer.type)
            for answer in out.authorities:
                nbr_authorities += 1
                assert answer.ttl == get_ttl(answer.type)

        # register service with default TTL
        expected_ttl = None
        for _ in range(3):
            _process_outgoing_packet(zc.generate_service_query(info))
        zc.registry.async_add(info)
        for _ in range(3):
            _process_outgoing_packet(zc.generate_service_broadcast(info, None))
        assert nbr_answers == 15 and nbr_additionals == 0 and nbr_authorities == 3
        nbr_answers = nbr_additionals = nbr_authorities = 0

        # query
        query = r.DNSOutgoing(const._FLAGS_QR_QUERY | const._FLAGS_AA)
        assert query.is_query() is True
        query.add_question(r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN))
        query.add_question(r.DNSQuestion(info.name, const._TYPE_SRV, const._CLASS_IN))
        query.add_question(r.DNSQuestion(info.name, const._TYPE_TXT, const._CLASS_IN))
        query.add_question(r.DNSQuestion(info.server or info.name, const._TYPE_A, const._CLASS_IN))
        question_answers = zc.query_handler.async_response(
            [r.DNSIncoming(packet) for packet in query.packets()], False
        )
        _process_outgoing_packet(construct_outgoing_multicast_answers(question_answers.mcast_aggregate))

        # The additonals should all be suppresed since they are all in the answers section
        # There will be one NSEC additional to indicate the lack of AAAA record
        #
        assert nbr_answers == 4 and nbr_additionals == 1 and nbr_authorities == 0
        nbr_answers = nbr_additionals = nbr_authorities = 0

        # unregister
        expected_ttl = 0
        zc.registry.async_remove(info)
        for _ in range(3):
            _process_outgoing_packet(zc.generate_service_broadcast(info, 0))
        assert nbr_answers == 15 and nbr_additionals == 0 and nbr_authorities == 0
        nbr_answers = nbr_additionals = nbr_authorities = 0

        expected_ttl = None
        for _ in range(3):
            _process_outgoing_packet(zc.generate_service_query(info))
        zc.registry.async_add(info)
        # register service with custom TTL
        expected_ttl = const._DNS_HOST_TTL * 2
        assert expected_ttl != const._DNS_HOST_TTL
        for _ in range(3):
            _process_outgoing_packet(zc.generate_service_broadcast(info, expected_ttl))
        assert nbr_answers == 15 and nbr_additionals == 0 and nbr_authorities == 3
        nbr_answers = nbr_additionals = nbr_authorities = 0

        # query
        expected_ttl = None
        query = r.DNSOutgoing(const._FLAGS_QR_QUERY | const._FLAGS_AA)
        query.add_question(r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN))
        query.add_question(r.DNSQuestion(info.name, const._TYPE_SRV, const._CLASS_IN))
        query.add_question(r.DNSQuestion(info.name, const._TYPE_TXT, const._CLASS_IN))
        query.add_question(r.DNSQuestion(info.server or info.name, const._TYPE_A, const._CLASS_IN))
        question_answers = zc.query_handler.async_response(
            [r.DNSIncoming(packet) for packet in query.packets()], False
        )
        _process_outgoing_packet(construct_outgoing_multicast_answers(question_answers.mcast_aggregate))

        # There will be one NSEC additional to indicate the lack of AAAA record
        assert nbr_answers == 4 and nbr_additionals == 1 and nbr_authorities == 0
        nbr_answers = nbr_additionals = nbr_authorities = 0

        # unregister
        expected_ttl = 0
        zc.registry.async_remove(info)
        for _ in range(3):
            _process_outgoing_packet(zc.generate_service_broadcast(info, 0))
        assert nbr_answers == 15 and nbr_additionals == 0 and nbr_authorities == 0
        nbr_answers = nbr_additionals = nbr_authorities = 0
        zc.close()

    def test_name_conflicts(self):
        # instantiate a zeroconf instance
        zc = Zeroconf(interfaces=['127.0.0.1'])
        type_ = "_homeassistant._tcp.local."
        name = "Home"
        registration_name = f"{name}.{type_}"

        info = ServiceInfo(
            type_,
            name=registration_name,
            server="random123.local.",
            addresses=[socket.inet_pton(socket.AF_INET, "1.2.3.4")],
            port=80,
            properties={"version": "1.0"},
        )
        zc.register_service(info)

        conflicting_info = ServiceInfo(
            type_,
            name=registration_name,
            server="random456.local.",
            addresses=[socket.inet_pton(socket.AF_INET, "4.5.6.7")],
            port=80,
            properties={"version": "1.0"},
        )
        with pytest.raises(r.NonUniqueNameException):
            zc.register_service(conflicting_info)
        zc.close()

    def test_register_and_lookup_type_by_uppercase_name(self):
        # instantiate a zeroconf instance
        zc = Zeroconf(interfaces=['127.0.0.1'])
        type_ = "_mylowertype._tcp.local."
        name = "Home"
        registration_name = f"{name}.{type_}"

        info = ServiceInfo(
            type_,
            name=registration_name,
            server="random123.local.",
            addresses=[socket.inet_pton(socket.AF_INET, "1.2.3.4")],
            port=80,
            properties={"version": "1.0"},
        )
        zc.register_service(info)
        _clear_cache(zc)
        info = ServiceInfo(type_, registration_name)
        info.load_from_cache(zc)
        assert info.addresses == []

        out = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        out.add_question(r.DNSQuestion(type_.upper(), const._TYPE_PTR, const._CLASS_IN))
        zc.send(out)
        time.sleep(1)
        info = ServiceInfo(type_, registration_name)
        info.load_from_cache(zc)
        assert info.addresses == [socket.inet_pton(socket.AF_INET, "1.2.3.4")]
        assert info.properties == {b"version": b"1.0"}
        zc.close()


def test_ptr_optimization():
    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])

    # service definition
    type_ = "_test-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )

    # register
    zc.register_service(info)

    # Verify we won't respond for 1s with the same multicast
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    query.add_question(r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN))
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    # Since we sent the PTR in the last second, they
    # should end up in the delayed at least one second bucket
    assert question_answers.mcast_aggregate_last_second

    # Clear the cache to allow responding again
    _clear_cache(zc)

    # Verify we will now respond
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    query.add_question(r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN))
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate_last_second
    has_srv = has_txt = has_a = False
    nbr_additionals = 0
    nbr_answers = len(question_answers.mcast_aggregate)
    additionals = set().union(*question_answers.mcast_aggregate.values())
    for answer in additionals:
        nbr_additionals += 1
        if answer.type == const._TYPE_SRV:
            has_srv = True
        elif answer.type == const._TYPE_TXT:
            has_txt = True
        elif answer.type == const._TYPE_A:
            has_a = True
    assert nbr_answers == 1 and nbr_additionals == 4
    # There will be one NSEC additional to indicate the lack of AAAA record

    assert has_srv and has_txt and has_a

    # unregister
    zc.unregister_service(info)
    zc.close()


@unittest.skipIf(not has_working_ipv6(), 'Requires IPv6')
@unittest.skipIf(os.environ.get('SKIP_IPV6'), 'IPv6 tests disabled')
def test_any_query_for_ptr():
    """Test that queries for ANY will return PTR records and the response is aggregated."""
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_anyptr._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    ipv6_address = socket.inet_pton(socket.AF_INET6, "2001:db8::1")
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, server_name, addresses=[ipv6_address])
    zc.registry.async_add(info)

    _clear_cache(zc)
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(type_, const._TYPE_ANY, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    mcast_answers = list(question_answers.mcast_aggregate)
    assert mcast_answers[0].name == type_
    assert mcast_answers[0].alias == registration_name  # type: ignore[attr-defined]
    # unregister
    zc.registry.async_remove(info)
    zc.close()


@unittest.skipIf(not has_working_ipv6(), 'Requires IPv6')
@unittest.skipIf(os.environ.get('SKIP_IPV6'), 'IPv6 tests disabled')
def test_aaaa_query():
    """Test that queries for AAAA records work and should respond right away."""
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_knownaaaservice._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    ipv6_address = socket.inet_pton(socket.AF_INET6, "2001:db8::1")
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, server_name, addresses=[ipv6_address])
    zc.registry.async_add(info)

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(server_name, const._TYPE_AAAA, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    mcast_answers = list(question_answers.mcast_now)
    assert mcast_answers[0].address == ipv6_address  # type: ignore[attr-defined]
    # unregister
    zc.registry.async_remove(info)
    zc.close()


@unittest.skipIf(not has_working_ipv6(), 'Requires IPv6')
@unittest.skipIf(os.environ.get('SKIP_IPV6'), 'IPv6 tests disabled')
def test_aaaa_query_upper_case():
    """Test that queries for AAAA records work and should respond right away with an upper case name."""
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_knownaaaservice._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    ipv6_address = socket.inet_pton(socket.AF_INET6, "2001:db8::1")
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, server_name, addresses=[ipv6_address])
    zc.registry.async_add(info)

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(server_name.upper(), const._TYPE_AAAA, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    mcast_answers = list(question_answers.mcast_now)
    assert mcast_answers[0].address == ipv6_address  # type: ignore[attr-defined]
    # unregister
    zc.registry.async_remove(info)
    zc.close()


@unittest.skipIf(not has_working_ipv6(), 'Requires IPv6')
@unittest.skipIf(os.environ.get('SKIP_IPV6'), 'IPv6 tests disabled')
def test_a_and_aaaa_record_fate_sharing():
    """Test that queries for AAAA always return A records in the additionals and should respond right away."""
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_a-and-aaaa-service._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    ipv6_address = socket.inet_pton(socket.AF_INET6, "2001:db8::1")
    ipv4_address = socket.inet_aton("10.0.1.2")
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[ipv6_address, ipv4_address]
    )
    aaaa_record = info.dns_addresses(version=r.IPVersion.V6Only)[0]
    a_record = info.dns_addresses(version=r.IPVersion.V4Only)[0]

    zc.registry.async_add(info)

    # Test AAAA query
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(server_name, const._TYPE_AAAA, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    additionals = set().union(*question_answers.mcast_now.values())
    assert aaaa_record in question_answers.mcast_now
    assert a_record in additionals
    assert len(question_answers.mcast_now) == 1
    assert len(additionals) == 1

    # Test A query
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(server_name, const._TYPE_A, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    additionals = set().union(*question_answers.mcast_now.values())
    assert a_record in question_answers.mcast_now
    assert aaaa_record in additionals
    assert len(question_answers.mcast_now) == 1
    assert len(additionals) == 1

    # unregister
    zc.registry.async_remove(info)
    zc.close()


def test_unicast_response():
    """Ensure we send a unicast response when the source port is not the MDNS port."""
    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])

    # service definition
    type_ = "_test-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    # register
    zc.registry.async_add(info)
    _clear_cache(zc)

    # query
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    query.add_question(r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN))
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], True
    )
    for answers in (question_answers.ucast, question_answers.mcast_aggregate):
        has_srv = has_txt = has_a = has_aaaa = has_nsec = False
        nbr_additionals = 0
        nbr_answers = len(answers)
        additionals = set().union(*answers.values())
        for answer in additionals:
            nbr_additionals += 1
            if answer.type == const._TYPE_SRV:
                has_srv = True
            elif answer.type == const._TYPE_TXT:
                has_txt = True
            elif answer.type == const._TYPE_A:
                has_a = True
            elif answer.type == const._TYPE_AAAA:
                has_aaaa = True
            elif answer.type == const._TYPE_NSEC:
                has_nsec = True
        # There will be one NSEC additional to indicate the lack of AAAA record
        assert nbr_answers == 1 and nbr_additionals == 4
        assert has_srv and has_txt and has_a and has_nsec
        assert not has_aaaa

    # unregister
    zc.registry.async_remove(info)
    zc.close()


@pytest.mark.asyncio
async def test_probe_answered_immediately():
    """Verify probes are responded to immediately."""
    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])

    # service definition
    type_ = "_test-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info)
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    query.add_question(question)
    query.add_authorative_answer(info.dns_pointer())
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.ucast
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    assert question_answers.mcast_now

    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True
    query.add_question(question)
    query.add_authorative_answer(info.dns_pointer())
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert question_answers.ucast
    assert question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    zc.close()


@pytest.mark.asyncio
async def test_probe_answered_immediately_with_uppercase_name():
    """Verify probes are responded to immediately with an uppercase name."""
    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])

    # service definition
    type_ = "_test-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info)
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type.upper(), const._TYPE_PTR, const._CLASS_IN)
    query.add_question(question)
    query.add_authorative_answer(info.dns_pointer())
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.ucast
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    assert question_answers.mcast_now

    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True
    query.add_question(question)
    query.add_authorative_answer(info.dns_pointer())
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert question_answers.ucast
    assert question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    zc.close()


def test_qu_response():
    """Handle multicast incoming with the QU bit set."""
    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])

    # service definition
    type_ = "_test-srvc-type._tcp.local."
    other_type_ = "_notthesame._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name}.{other_type_}"
    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    info2 = ServiceInfo(
        other_type_,
        registration_name2,
        80,
        0,
        0,
        desc,
        "ash-other.local.",
        addresses=[socket.inet_aton("10.0.4.2")],
    )
    # register
    zc.register_service(info)

    def _validate_complete_response(answers):
        has_srv = has_txt = has_a = has_aaaa = has_nsec = False
        nbr_answers = len(answers)
        additionals = set().union(*answers.values())
        nbr_additionals = len(additionals)

        for answer in additionals:
            if answer.type == const._TYPE_SRV:
                has_srv = True
            elif answer.type == const._TYPE_TXT:
                has_txt = True
            elif answer.type == const._TYPE_A:
                has_a = True
            elif answer.type == const._TYPE_AAAA:
                has_aaaa = True
            elif answer.type == const._TYPE_NSEC:
                has_nsec = True
        assert nbr_answers == 1 and nbr_additionals == 4
        assert has_srv and has_txt and has_a and has_nsec
        assert not has_aaaa

    # With QU should respond to only unicast when the answer has been recently multicast
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)

    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    _validate_complete_response(question_answers.ucast)
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    _clear_cache(zc)
    # With QU should respond to only multicast since the response hasn't been seen since 75% of the ttl
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.ucast
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate
    _validate_complete_response(question_answers.mcast_now)

    # With QU set and an authorative answer (probe) should respond to both unitcast and multicast since the response hasn't been seen since 75% of the ttl
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)
    query.add_authorative_answer(info2.dns_pointer())
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    _validate_complete_response(question_answers.ucast)
    _validate_complete_response(question_answers.mcast_now)

    _inject_response(
        zc, r.DNSIncoming(construct_outgoing_multicast_answers(question_answers.mcast_now).packets()[0])
    )
    # With the cache repopulated; should respond to only unicast when the answer has been recently multicast
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)
    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    _validate_complete_response(question_answers.ucast)
    # unregister
    zc.unregister_service(info)
    zc.close()


def test_known_answer_supression():
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_knownanswersv8._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info)

    now = current_time_millis()
    _clear_cache(zc)
    # Test PTR supression
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(type_, const._TYPE_PTR, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(type_, const._TYPE_PTR, const._CLASS_IN)
    generated.add_question(question)
    generated.add_answer_at_time(info.dns_pointer(), now)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    # Test A supression
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(server_name, const._TYPE_A, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(server_name, const._TYPE_A, const._CLASS_IN)
    generated.add_question(question)
    for dns_address in info.dns_addresses():
        generated.add_answer_at_time(dns_address, now)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    # Test NSEC record returned when there is no AAAA record and we expectly ask
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(server_name, const._TYPE_AAAA, const._CLASS_IN)
    generated.add_question(question)
    for dns_address in info.dns_addresses():
        generated.add_answer_at_time(dns_address, now)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    expected_nsec_record = cast(r.DNSNsec, list(question_answers.mcast_now)[0])
    assert const._TYPE_A not in expected_nsec_record.rdtypes
    assert const._TYPE_AAAA in expected_nsec_record.rdtypes
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    # Test SRV supression
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(registration_name, const._TYPE_SRV, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(registration_name, const._TYPE_SRV, const._CLASS_IN)
    generated.add_question(question)
    generated.add_answer_at_time(info.dns_service(), now)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    # Test TXT supression
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(registration_name, const._TYPE_TXT, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(registration_name, const._TYPE_TXT, const._CLASS_IN)
    generated.add_question(question)
    generated.add_answer_at_time(info.dns_text(), now)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    # unregister
    zc.registry.async_remove(info)
    zc.close()


def test_multi_packet_known_answer_supression():
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_handlermultis._tcp.local."
    name = "knownname"
    name2 = "knownname2"
    name3 = "knownname3"

    registration_name = f"{name}.{type_}"
    registration2_name = f"{name2}.{type_}"
    registration3_name = f"{name3}.{type_}"

    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    server_name2 = "ash-3.local."
    server_name3 = "ash-4.local."

    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[socket.inet_aton("10.0.1.2")]
    )
    info2 = ServiceInfo(
        type_, registration2_name, 80, 0, 0, desc, server_name2, addresses=[socket.inet_aton("10.0.1.2")]
    )
    info3 = ServiceInfo(
        type_, registration3_name, 80, 0, 0, desc, server_name3, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info)
    zc.registry.async_add(info2)
    zc.registry.async_add(info3)

    now = current_time_millis()
    _clear_cache(zc)
    # Test PTR supression
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(type_, const._TYPE_PTR, const._CLASS_IN)
    generated.add_question(question)
    for _ in range(1000):
        # Add so many answers we end up with another packet
        generated.add_answer_at_time(info.dns_pointer(), now)
    generated.add_answer_at_time(info2.dns_pointer(), now)
    generated.add_answer_at_time(info3.dns_pointer(), now)
    packets = generated.packets()
    assert len(packets) > 1
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    # unregister
    zc.registry.async_remove(info)
    zc.registry.async_remove(info2)
    zc.registry.async_remove(info3)
    zc.close()


def test_known_answer_supression_service_type_enumeration_query():
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_otherknown._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info)

    type_2 = "_otherknown2._tcp.local."
    name = "knownname"
    registration_name2 = f"{name}.{type_2}"
    desc = {'path': '/~paulsm/'}
    server_name2 = "ash-3.local."
    info2 = ServiceInfo(
        type_2, registration_name2, 80, 0, 0, desc, server_name2, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info2)
    now = current_time_millis()
    _clear_cache(zc)

    # Test PTR supression
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(const._SERVICE_TYPE_ENUMERATION_NAME, const._TYPE_PTR, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(const._SERVICE_TYPE_ENUMERATION_NAME, const._TYPE_PTR, const._CLASS_IN)
    generated.add_question(question)
    generated.add_answer_at_time(
        r.DNSPointer(
            const._SERVICE_TYPE_ENUMERATION_NAME,
            const._TYPE_PTR,
            const._CLASS_IN,
            const._DNS_OTHER_TTL,
            type_,
        ),
        now,
    )
    generated.add_answer_at_time(
        r.DNSPointer(
            const._SERVICE_TYPE_ENUMERATION_NAME,
            const._TYPE_PTR,
            const._CLASS_IN,
            const._DNS_OTHER_TTL,
            type_2,
        ),
        now,
    )
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    # unregister
    zc.registry.async_remove(info)
    zc.registry.async_remove(info2)
    zc.close()


def test_upper_case_enumeration_query():
    zc = Zeroconf(interfaces=['127.0.0.1'])
    type_ = "_otherknown._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info)

    type_2 = "_otherknown2._tcp.local."
    name = "knownname"
    registration_name2 = f"{name}.{type_2}"
    desc = {'path': '/~paulsm/'}
    server_name2 = "ash-3.local."
    info2 = ServiceInfo(
        type_2, registration_name2, 80, 0, 0, desc, server_name2, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info2)
    _clear_cache(zc)

    # Test PTR supression
    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(const._SERVICE_TYPE_ENUMERATION_NAME.upper(), const._TYPE_PTR, const._CLASS_IN)
    generated.add_question(question)
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    # unregister
    zc.registry.async_remove(info)
    zc.registry.async_remove(info2)
    zc.close()


# This test uses asyncio because it needs to access the cache directly
# which is not threadsafe
@pytest.mark.asyncio
async def test_qu_response_only_sends_additionals_if_sends_answer():
    """Test that a QU response does not send additionals unless it sends the answer as well."""
    # instantiate a zeroconf instance
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf

    type_ = "_addtest1._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "ash-2.local."
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info)

    type_2 = "_addtest2._tcp.local."
    name = "knownname"
    registration_name2 = f"{name}.{type_2}"
    desc = {'path': '/~paulsm/'}
    server_name2 = "ash-3.local."
    info2 = ServiceInfo(
        type_2, registration_name2, 80, 0, 0, desc, server_name2, addresses=[socket.inet_aton("10.0.1.2")]
    )
    zc.registry.async_add(info2)

    ptr_record = info.dns_pointer()

    # Add the PTR record to the cache
    zc.cache.async_add_records([ptr_record])

    # Add the A record to the cache with 50% ttl remaining
    a_record = info.dns_addresses()[0]
    a_record.set_created_ttl(current_time_millis() - (a_record.ttl * 1000 / 2), a_record.ttl)
    assert not a_record.is_recent(current_time_millis())
    info._dns_address_cache = None  # we are mutating the record so clear the cache
    zc.cache.async_add_records([a_record])

    # With QU should respond to only unicast when the answer has been recently multicast
    # even if the additional has not been recently multicast
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)

    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    additionals = set().union(*question_answers.ucast.values())
    assert a_record in additionals
    assert ptr_record in question_answers.ucast

    # Remove the 50% A record and add a 100% A record
    zc.cache.async_remove_records([a_record])
    a_record = info.dns_addresses()[0]
    assert a_record.is_recent(current_time_millis())
    zc.cache.async_add_records([a_record])
    # With QU should respond to only unicast when the answer has been recently multicast
    # even if the additional has not been recently multicast
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)

    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    additionals = set().union(*question_answers.ucast.values())
    assert a_record in additionals
    assert ptr_record in question_answers.ucast

    # Remove the 100% PTR record and add a 50% PTR record
    zc.cache.async_remove_records([ptr_record])
    ptr_record.set_created_ttl(current_time_millis() - (ptr_record.ttl * 1000 / 2), ptr_record.ttl)
    assert not ptr_record.is_recent(current_time_millis())
    zc.cache.async_add_records([ptr_record])
    # With QU should respond to only multicast since the has less
    # than 75% of its ttl remaining
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)

    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.ucast
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    additionals = set().union(*question_answers.mcast_now.values())
    assert a_record in additionals
    assert info.dns_text() in additionals
    assert info.dns_service() in additionals
    assert ptr_record in question_answers.mcast_now

    # Ask 2 QU questions, with info the PTR is at 50%, with info2 the PTR is at 100%
    # We should get back a unicast reply for info2, but info should be multicasted since its within 75% of its TTL
    # With QU should respond to only multicast since the has less
    # than 75% of its ttl remaining
    query = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)

    question = r.DNSQuestion(info2.type, const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True  # Set the QU bit
    assert question.unicast is True
    query.add_question(question)
    zc.cache.async_add_records([info2.dns_pointer()])  # Add 100% TTL for info2 to the cache

    question_answers = zc.query_handler.async_response(
        [r.DNSIncoming(packet) for packet in query.packets()], False
    )
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second

    mcast_now_additionals = set().union(*question_answers.mcast_now.values())
    assert a_record in mcast_now_additionals
    assert info.dns_text() in mcast_now_additionals
    assert info.dns_addresses()[0] in mcast_now_additionals
    assert info.dns_pointer() in question_answers.mcast_now

    ucast_additionals = set().union(*question_answers.ucast.values())
    assert info2.dns_pointer() in question_answers.ucast
    assert info2.dns_text() in ucast_additionals
    assert info2.dns_service() in ucast_additionals
    assert info2.dns_addresses()[0] in ucast_additionals

    # unregister
    zc.registry.async_remove(info)
    await aiozc.async_close()


# This test uses asyncio because it needs to access the cache directly
# which is not threadsafe
@pytest.mark.asyncio
async def test_cache_flush_bit():
    """Test that the cache flush bit sets the TTL to one for matching records."""
    # instantiate a zeroconf instance
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf

    type_ = "_cacheflush._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "server-uu1.local."
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[socket.inet_aton("10.0.1.2")]
    )
    a_record = info.dns_addresses()[0]
    zc.cache.async_add_records([info.dns_pointer(), a_record, info.dns_text(), info.dns_service()])

    info.addresses = [socket.inet_aton("10.0.1.5"), socket.inet_aton("10.0.1.6")]
    new_records = info.dns_addresses()
    for new_record in new_records:
        assert new_record.unique is True

    original_a_record = zc.cache.async_get_unique(a_record)
    # Do the run within 1s to verify the original record is not going to be expired
    out = r.DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA, multicast=True)
    for answer in new_records:
        out.add_answer_at_time(answer, 0)
    for packet in out.packets():
        zc.record_manager.async_updates_from_response(r.DNSIncoming(packet))
    assert zc.cache.async_get_unique(a_record) is original_a_record
    assert original_a_record is not None
    assert original_a_record.ttl != 1
    for record in new_records:
        assert zc.cache.async_get_unique(record) is not None

    original_a_record.created = current_time_millis() - 1500

    # Do the run within 1s to verify the original record is not going to be expired
    out = r.DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA, multicast=True)
    for answer in new_records:
        out.add_answer_at_time(answer, 0)
    for packet in out.packets():
        zc.record_manager.async_updates_from_response(r.DNSIncoming(packet))
    assert original_a_record.ttl == 1
    for record in new_records:
        assert zc.cache.async_get_unique(record) is not None

    cached_records = [zc.cache.async_get_unique(record) for record in new_records]
    for cached_record in cached_records:
        assert cached_record is not None
        cached_record.created = current_time_millis() - 1500

    fresh_address = socket.inet_aton("4.4.4.4")
    info.addresses = [fresh_address]
    # Do the run within 1s to verify the two new records get marked as expired
    out = r.DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA, multicast=True)
    for answer in info.dns_addresses():
        out.add_answer_at_time(answer, 0)
    for packet in out.packets():
        zc.record_manager.async_updates_from_response(r.DNSIncoming(packet))
    for cached_record in cached_records:
        assert cached_record is not None
        assert cached_record.ttl == 1

    for entry in zc.cache.async_all_by_details(server_name, const._TYPE_A, const._CLASS_IN):
        assert isinstance(entry, r.DNSAddress)
        if entry.address == fresh_address:
            assert entry.ttl > 1
        else:
            assert entry.ttl == 1

    # Wait for the ttl 1 records to expire
    await asyncio.sleep(1.1)

    loaded_info = r.ServiceInfo(type_, registration_name)
    loaded_info.load_from_cache(zc)
    assert loaded_info.addresses == info.addresses

    await aiozc.async_close()


# This test uses asyncio because it needs to access the cache directly
# which is not threadsafe
@pytest.mark.asyncio
async def test_record_update_manager_add_listener_callsback_existing_records():
    """Test that the RecordUpdateManager will callback existing records."""

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc: Zeroconf = aiozc.zeroconf
    updated = []

    class MyListener(r.RecordUpdateListener):
        """A RecordUpdateListener that does not implement update_records."""

        def async_update_records(self, zc: 'Zeroconf', now: float, records: List[r.RecordUpdate]) -> None:
            """Update multiple records in one shot."""
            updated.extend(records)

    type_ = "_cacheflush._tcp.local."
    name = "knownname"
    registration_name = f"{name}.{type_}"
    desc = {'path': '/~paulsm/'}
    server_name = "server-uu1.local."
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, server_name, addresses=[socket.inet_aton("10.0.1.2")]
    )
    a_record = info.dns_addresses()[0]
    ptr_record = info.dns_pointer()
    zc.cache.async_add_records([ptr_record, a_record, info.dns_text(), info.dns_service()])

    listener = MyListener()

    zc.add_listener(
        listener,
        [
            r.DNSQuestion(type_, const._TYPE_PTR, const._CLASS_IN),
            r.DNSQuestion(server_name, const._TYPE_A, const._CLASS_IN),
        ],
    )
    await asyncio.sleep(0)  # flush out the call_soon_threadsafe

    assert {record.new for record in updated} == {ptr_record, a_record}

    # The old records should be None so we trigger Add events
    # in service browsers instead of Update events
    assert {record.old for record in updated} == {None}

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_questions_query_handler_populates_the_question_history_from_qm_questions():
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    now = current_time_millis()
    _clear_cache(zc)

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion("_hap._tcp._local.", const._TYPE_PTR, const._CLASS_IN)
    question.unicast = False
    known_answer = r.DNSPointer(
        "_hap._tcp.local.", const._TYPE_PTR, const._CLASS_IN, 10000, 'known-to-other._hap._tcp.local.'
    )
    generated.add_question(question)
    generated.add_answer_at_time(known_answer, 0)
    now = r.current_time_millis()
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    assert zc.question_history.suppresses(question, now, {known_answer})

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_questions_query_handler_does_not_put_qu_questions_in_history():
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    now = current_time_millis()
    _clear_cache(zc)

    generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
    question = r.DNSQuestion("_hap._tcp._local.", const._TYPE_PTR, const._CLASS_IN)
    question.unicast = True
    known_answer = r.DNSPointer(
        "_hap._tcp.local.", const._TYPE_PTR, const._CLASS_IN, 10000, 'known-to-other._hap._tcp.local.'
    )
    generated.add_question(question)
    generated.add_answer_at_time(known_answer, 0)
    now = r.current_time_millis()
    packets = generated.packets()
    question_answers = zc.query_handler.async_response([r.DNSIncoming(packet) for packet in packets], False)
    assert not question_answers.ucast
    assert not question_answers.mcast_now
    assert not question_answers.mcast_aggregate
    assert not question_answers.mcast_aggregate_last_second
    assert not zc.question_history.suppresses(question, now, {known_answer})

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_guard_against_low_ptr_ttl():
    """Ensure we enforce a minimum for PTR record ttls to avoid excessive refresh queries from ServiceBrowsers.

    Some poorly designed IoT devices can set excessively low PTR
    TTLs would will cause ServiceBrowsers to flood the network
    with excessive refresh queries.
    """
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    # Apple uses a 15s minimum TTL, however we do not have the same
    # level of rate limit and safe guards so we use 1/4 of the recommended value
    answer_with_low_ttl = r.DNSPointer(
        "myservicelow_tcp._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN | const._CLASS_UNIQUE,
        2,
        'low.local.',
    )
    answer_with_normal_ttl = r.DNSPointer(
        "myservicelow_tcp._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN | const._CLASS_UNIQUE,
        const._DNS_OTHER_TTL,
        'normal.local.',
    )
    good_bye_answer = r.DNSPointer(
        "myservicelow_tcp._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN | const._CLASS_UNIQUE,
        0,
        'goodbye.local.',
    )
    # TTL should be adjusted to a safe value
    response = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
    response.add_answer_at_time(answer_with_low_ttl, 0)
    response.add_answer_at_time(answer_with_normal_ttl, 0)
    response.add_answer_at_time(good_bye_answer, 0)
    incoming = r.DNSIncoming(response.packets()[0])
    zc.record_manager.async_updates_from_response(incoming)

    incoming_answer_low = zc.cache.async_get_unique(answer_with_low_ttl)
    assert incoming_answer_low is not None
    assert incoming_answer_low.ttl == const._DNS_PTR_MIN_TTL
    incoming_answer_normal = zc.cache.async_get_unique(answer_with_normal_ttl)
    assert incoming_answer_normal is not None
    assert incoming_answer_normal.ttl == const._DNS_OTHER_TTL
    assert zc.cache.async_get_unique(good_bye_answer) is None
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_duplicate_goodbye_answers_in_packet():
    """Ensure we do not throw an exception when there are duplicate goodbye records in a packet."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    answer_with_normal_ttl = r.DNSPointer(
        "myservicelow_tcp._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN | const._CLASS_UNIQUE,
        const._DNS_OTHER_TTL,
        'host.local.',
    )
    good_bye_answer = r.DNSPointer(
        "myservicelow_tcp._tcp.local.",
        const._TYPE_PTR,
        const._CLASS_IN | const._CLASS_UNIQUE,
        0,
        'host.local.',
    )
    response = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
    response.add_answer_at_time(answer_with_normal_ttl, 0)
    incoming = r.DNSIncoming(response.packets()[0])
    zc.record_manager.async_updates_from_response(incoming)

    response = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
    response.add_answer_at_time(good_bye_answer, 0)
    response.add_answer_at_time(good_bye_answer, 0)
    incoming = r.DNSIncoming(response.packets()[0])
    zc.record_manager.async_updates_from_response(incoming)
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_response_aggregation_timings(run_isolated):
    """Verify multicast respones are aggregated."""
    type_ = "_mservice._tcp.local."
    type_2 = "_mservice2._tcp.local."
    type_3 = "_mservice3._tcp.local."

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.zeroconf.async_wait_for_start()

    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name}.{type_2}"
    registration_name3 = f"{name}.{type_3}"

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    info2 = ServiceInfo(
        type_2, registration_name2, 80, 0, 0, desc, "ash-4.local.", addresses=[socket.inet_aton("10.0.1.3")]
    )
    info3 = ServiceInfo(
        type_3, registration_name3, 80, 0, 0, desc, "ash-4.local.", addresses=[socket.inet_aton("10.0.1.3")]
    )
    aiozc.zeroconf.registry.async_add(info)
    aiozc.zeroconf.registry.async_add(info2)
    aiozc.zeroconf.registry.async_add(info3)

    query = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    question = r.DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    query.add_question(question)

    query2 = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    question2 = r.DNSQuestion(info2.type, const._TYPE_PTR, const._CLASS_IN)
    query2.add_question(question2)

    query3 = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    question3 = r.DNSQuestion(info3.type, const._TYPE_PTR, const._CLASS_IN)
    query3.add_question(question3)

    query4 = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    query4.add_question(question)
    query4.add_question(question2)

    zc = aiozc.zeroconf
    protocol = zc.engine.protocols[0]

    with unittest.mock.patch.object(aiozc.zeroconf, "async_send") as send_mock:
        protocol.datagram_received(query.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        protocol.datagram_received(query2.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        protocol.datagram_received(query.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        await asyncio.sleep(0.7)

        # Should aggregate into a single answer with up to a 500ms + 120ms delay
        calls = send_mock.mock_calls
        assert len(calls) == 1
        outgoing = send_mock.call_args[0][0]
        incoming = r.DNSIncoming(outgoing.packets()[0])
        zc.record_manager.async_updates_from_response(incoming)
        assert info.dns_pointer() in incoming.answers()
        assert info2.dns_pointer() in incoming.answers()
        send_mock.reset_mock()

        protocol.datagram_received(query3.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        await asyncio.sleep(0.3)

        # Should send within 120ms since there are no other
        # answers to aggregate with
        calls = send_mock.mock_calls
        assert len(calls) == 1
        outgoing = send_mock.call_args[0][0]
        incoming = r.DNSIncoming(outgoing.packets()[0])
        zc.record_manager.async_updates_from_response(incoming)
        assert info3.dns_pointer() in incoming.answers()
        send_mock.reset_mock()

        # Because the response was sent in the last second we need to make
        # sure the next answer is delayed at least a second
        aiozc.zeroconf.engine.protocols[0].datagram_received(
            query4.packets()[0], ('127.0.0.1', const._MDNS_PORT)
        )
        await asyncio.sleep(0.5)

        # After 0.5 seconds it should not have been sent
        # Protect the network against excessive packet flooding
        # https://datatracker.ietf.org/doc/html/rfc6762#section-14
        calls = send_mock.mock_calls
        assert len(calls) == 0
        send_mock.reset_mock()

        await asyncio.sleep(1.2)
        calls = send_mock.mock_calls
        assert len(calls) == 1
        outgoing = send_mock.call_args[0][0]
        incoming = r.DNSIncoming(outgoing.packets()[0])
        assert info.dns_pointer() in incoming.answers()

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_response_aggregation_timings_multiple(run_isolated, disable_duplicate_packet_suppression):
    """Verify multicast responses that are aggregated do not take longer than 620ms to send.

    620ms is the maximum random delay of 120ms and 500ms additional for aggregation."""
    type_2 = "_mservice2._tcp.local."

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.zeroconf.async_wait_for_start()

    name = "xxxyyy"
    registration_name2 = f"{name}.{type_2}"

    desc = {'path': '/~paulsm/'}
    info2 = ServiceInfo(
        type_2, registration_name2, 80, 0, 0, desc, "ash-4.local.", addresses=[socket.inet_aton("10.0.1.3")]
    )
    aiozc.zeroconf.registry.async_add(info2)

    query2 = r.DNSOutgoing(const._FLAGS_QR_QUERY, multicast=True)
    question2 = r.DNSQuestion(info2.type, const._TYPE_PTR, const._CLASS_IN)
    query2.add_question(question2)

    zc = aiozc.zeroconf
    protocol = zc.engine.protocols[0]

    with unittest.mock.patch.object(aiozc.zeroconf, "async_send") as send_mock:
        send_mock.reset_mock()
        protocol.datagram_received(query2.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        await asyncio.sleep(0.2)
        calls = send_mock.mock_calls
        assert len(calls) == 1
        outgoing = send_mock.call_args[0][0]
        incoming = r.DNSIncoming(outgoing.packets()[0])
        zc.record_manager.async_updates_from_response(incoming)
        assert info2.dns_pointer() in incoming.answers()

        send_mock.reset_mock()
        protocol.datagram_received(query2.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        await asyncio.sleep(1.2)
        calls = send_mock.mock_calls
        assert len(calls) == 1
        outgoing = send_mock.call_args[0][0]
        incoming = r.DNSIncoming(outgoing.packets()[0])
        zc.record_manager.async_updates_from_response(incoming)
        assert info2.dns_pointer() in incoming.answers()

        send_mock.reset_mock()
        protocol.datagram_received(query2.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        protocol.datagram_received(query2.packets()[0], ('127.0.0.1', const._MDNS_PORT))
        # The delay should increase with two packets and
        # 900ms is beyond the maximum aggregation delay
        # when there is no network protection delay
        await asyncio.sleep(0.9)
        calls = send_mock.mock_calls
        assert len(calls) == 0

        # 1000ms  (1s network protection delays)
        # - 900ms (already slept)
        # + 120ms (maximum random delay)
        # + 200ms (maximum protected aggregation delay)
        # +  20ms (execution time)
        await asyncio.sleep(millis_to_seconds(1000 - 900 + 120 + 200 + 20))
        calls = send_mock.mock_calls
        assert len(calls) == 1
        outgoing = send_mock.call_args[0][0]
        incoming = r.DNSIncoming(outgoing.packets()[0])
        zc.record_manager.async_updates_from_response(incoming)
        assert info2.dns_pointer() in incoming.answers()


@pytest.mark.asyncio
async def test_response_aggregation_random_delay():
    """Verify the random delay for outgoing multicast will coalesce into a single group

    When the random delay is shorter than the last outgoing group,
    the groups should be combined.
    """
    type_ = "_mservice._tcp.local."
    type_2 = "_mservice2._tcp.local."
    type_3 = "_mservice3._tcp.local."
    type_4 = "_mservice4._tcp.local."
    type_5 = "_mservice5._tcp.local."

    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name}.{type_2}"
    registration_name3 = f"{name}.{type_3}"
    registration_name4 = f"{name}.{type_4}"
    registration_name5 = f"{name}.{type_5}"

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-1.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    info2 = ServiceInfo(
        type_2, registration_name2, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.3")]
    )
    info3 = ServiceInfo(
        type_3, registration_name3, 80, 0, 0, desc, "ash-3.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    info4 = ServiceInfo(
        type_4, registration_name4, 80, 0, 0, desc, "ash-4.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    info5 = ServiceInfo(
        type_5, registration_name5, 80, 0, 0, desc, "ash-5.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    mocked_zc = unittest.mock.MagicMock()
    outgoing_queue = MulticastOutgoingQueue(mocked_zc, 0, 500)

    now = current_time_millis()
    with unittest.mock.patch.object(multicast_outgoing_queue, "MULTICAST_DELAY_RANDOM_INTERVAL", (500, 600)):
        outgoing_queue.async_add(now, {info.dns_pointer(): set()})

    # The second group should always be coalesced into first group since it will always come before
    with unittest.mock.patch.object(multicast_outgoing_queue, "MULTICAST_DELAY_RANDOM_INTERVAL", (300, 400)):
        outgoing_queue.async_add(now, {info2.dns_pointer(): set()})

    # The third group should always be coalesced into first group since it will always come before
    with unittest.mock.patch.object(multicast_outgoing_queue, "MULTICAST_DELAY_RANDOM_INTERVAL", (100, 200)):
        outgoing_queue.async_add(now, {info3.dns_pointer(): set(), info4.dns_pointer(): set()})

    assert len(outgoing_queue.queue) == 1
    assert info.dns_pointer() in outgoing_queue.queue[0].answers
    assert info2.dns_pointer() in outgoing_queue.queue[0].answers
    assert info3.dns_pointer() in outgoing_queue.queue[0].answers
    assert info4.dns_pointer() in outgoing_queue.queue[0].answers

    # The forth group should not be coalesced because its scheduled after the last group in the queue
    with unittest.mock.patch.object(multicast_outgoing_queue, "MULTICAST_DELAY_RANDOM_INTERVAL", (700, 800)):
        outgoing_queue.async_add(now, {info5.dns_pointer(): set()})

    assert len(outgoing_queue.queue) == 2
    assert info.dns_pointer() not in outgoing_queue.queue[1].answers
    assert info2.dns_pointer() not in outgoing_queue.queue[1].answers
    assert info3.dns_pointer() not in outgoing_queue.queue[1].answers
    assert info4.dns_pointer() not in outgoing_queue.queue[1].answers
    assert info5.dns_pointer() in outgoing_queue.queue[1].answers


@pytest.mark.asyncio
async def test_future_answers_are_removed_on_send():
    """Verify any future answers scheduled to be sent are removed when we send."""
    type_ = "_mservice._tcp.local."
    type_2 = "_mservice2._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name}.{type_2}"

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-1.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )
    info2 = ServiceInfo(
        type_2, registration_name2, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.3")]
    )
    mocked_zc = unittest.mock.MagicMock()
    outgoing_queue = MulticastOutgoingQueue(mocked_zc, 0, 0)

    now = current_time_millis()
    with unittest.mock.patch.object(multicast_outgoing_queue, "MULTICAST_DELAY_RANDOM_INTERVAL", (1, 1)):
        outgoing_queue.async_add(now, {info.dns_pointer(): set()})

    assert len(outgoing_queue.queue) == 1

    with unittest.mock.patch.object(multicast_outgoing_queue, "MULTICAST_DELAY_RANDOM_INTERVAL", (2, 2)):
        outgoing_queue.async_add(now, {info.dns_pointer(): set()})

    assert len(outgoing_queue.queue) == 2

    with unittest.mock.patch.object(
        multicast_outgoing_queue, "MULTICAST_DELAY_RANDOM_INTERVAL", (1000, 1000)
    ):
        outgoing_queue.async_add(now, {info2.dns_pointer(): set()})
        outgoing_queue.async_add(now, {info.dns_pointer(): set()})

    assert len(outgoing_queue.queue) == 3

    await asyncio.sleep(0.1)
    outgoing_queue.async_ready()

    assert len(outgoing_queue.queue) == 1
    # The answer should get removed because we just sent it
    assert info.dns_pointer() not in outgoing_queue.queue[0].answers

    # But the one we have not sent yet shoudl still go out later
    assert info2.dns_pointer() in outgoing_queue.queue[0].answers


@pytest.mark.asyncio
async def test_add_listener_warns_when_not_using_record_update_listener(caplog):
    """Log when a listener is added that is not using RecordUpdateListener as a base class."""

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc: Zeroconf = aiozc.zeroconf
    updated = []

    class MyListener:
        """A RecordUpdateListener that does not implement update_records."""

        def async_update_records(self, zc: 'Zeroconf', now: float, records: List[r.RecordUpdate]) -> None:
            """Update multiple records in one shot."""
            updated.extend(records)

    zc.add_listener(MyListener(), None)  # type: ignore[arg-type]
    await asyncio.sleep(0)  # flush out any call soons
    assert "listeners passed to async_add_listener must inherit from RecordUpdateListener" in caplog.text

    await aiozc.async_close()
