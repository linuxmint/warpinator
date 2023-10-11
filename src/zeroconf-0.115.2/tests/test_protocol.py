#!/usr/bin/env python


""" Unit tests for zeroconf._protocol """

import copy
import logging
import os
import socket
import struct
import unittest
import unittest.mock
from typing import cast

import zeroconf as r
from zeroconf import DNSHinfo, DNSIncoming, DNSText, const, current_time_millis

from . import has_working_ipv6

log = logging.getLogger('zeroconf')
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


class PacketGeneration(unittest.TestCase):
    def test_parse_own_packet_simple(self):
        generated = r.DNSOutgoing(0)
        r.DNSIncoming(generated.packets()[0])

    def test_parse_own_packet_simple_unicast(self):
        generated = r.DNSOutgoing(0, False)
        r.DNSIncoming(generated.packets()[0])

    def test_parse_own_packet_flags(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        r.DNSIncoming(generated.packets()[0])

    def test_parse_own_packet_question(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        generated.add_question(r.DNSQuestion("testname.local.", const._TYPE_SRV, const._CLASS_IN))
        r.DNSIncoming(generated.packets()[0])

    def test_parse_own_packet_nsec(self):
        answer = r.DNSNsec(
            'eufy HomeBase2-2464._hap._tcp.local.',
            const._TYPE_NSEC,
            const._CLASS_IN | const._CLASS_UNIQUE,
            const._DNS_OTHER_TTL,
            'eufy HomeBase2-2464._hap._tcp.local.',
            [const._TYPE_TXT, const._TYPE_SRV],
        )

        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        generated.add_answer_at_time(answer, 0)
        parsed = r.DNSIncoming(generated.packets()[0])
        assert answer in parsed.answers()

        # Types > 255 should be ignored
        answer_invalid_types = r.DNSNsec(
            'eufy HomeBase2-2464._hap._tcp.local.',
            const._TYPE_NSEC,
            const._CLASS_IN | const._CLASS_UNIQUE,
            const._DNS_OTHER_TTL,
            'eufy HomeBase2-2464._hap._tcp.local.',
            [const._TYPE_TXT, const._TYPE_SRV, 1000],
        )
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        generated.add_answer_at_time(answer_invalid_types, 0)
        parsed = r.DNSIncoming(generated.packets()[0])
        assert answer in parsed.answers()

    def test_parse_own_packet_response(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        generated.add_answer_at_time(
            r.DNSService(
                "æøå.local.",
                const._TYPE_SRV,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                0,
                0,
                80,
                "foo.local.",
            ),
            0,
        )
        parsed = r.DNSIncoming(generated.packets()[0])
        assert len(generated.answers) == 1
        assert len(generated.answers) == len(parsed.answers())

    def test_adding_empty_answer(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        generated.add_answer_at_time(
            None,
            0,
        )
        generated.add_answer_at_time(
            r.DNSService(
                "æøå.local.",
                const._TYPE_SRV,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                0,
                0,
                80,
                "foo.local.",
            ),
            0,
        )
        parsed = r.DNSIncoming(generated.packets()[0])
        assert len(generated.answers) == 1
        assert len(generated.answers) == len(parsed.answers())

    def test_adding_expired_answer(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        generated.add_answer_at_time(
            r.DNSService(
                "æøå.local.",
                const._TYPE_SRV,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                0,
                0,
                80,
                "foo.local.",
            ),
            current_time_millis() + 1000000,
        )
        parsed = r.DNSIncoming(generated.packets()[0])
        assert len(generated.answers) == 0
        assert len(generated.answers) == len(parsed.answers())

    def test_match_question(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        question = r.DNSQuestion("testname.local.", const._TYPE_SRV, const._CLASS_IN)
        generated.add_question(question)
        parsed = r.DNSIncoming(generated.packets()[0])
        assert len(generated.questions) == 1
        assert len(generated.questions) == len(parsed.questions)
        assert question == parsed.questions[0]

    def test_suppress_answer(self):
        query_generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        question = r.DNSQuestion("testname.local.", const._TYPE_SRV, const._CLASS_IN)
        query_generated.add_question(question)
        answer1 = r.DNSService(
            "testname1.local.",
            const._TYPE_SRV,
            const._CLASS_IN | const._CLASS_UNIQUE,
            const._DNS_HOST_TTL,
            0,
            0,
            80,
            "foo.local.",
        )
        staleanswer2 = r.DNSService(
            "testname2.local.",
            const._TYPE_SRV,
            const._CLASS_IN | const._CLASS_UNIQUE,
            const._DNS_HOST_TTL / 2,
            0,
            0,
            80,
            "foo.local.",
        )
        answer2 = r.DNSService(
            "testname2.local.",
            const._TYPE_SRV,
            const._CLASS_IN | const._CLASS_UNIQUE,
            const._DNS_HOST_TTL,
            0,
            0,
            80,
            "foo.local.",
        )
        query_generated.add_answer_at_time(answer1, 0)
        query_generated.add_answer_at_time(staleanswer2, 0)
        query = r.DNSIncoming(query_generated.packets()[0])

        # Should be suppressed
        response = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        response.add_answer(query, answer1)
        assert len(response.answers) == 0

        # Should not be suppressed, TTL in query is too short
        response.add_answer(query, answer2)
        assert len(response.answers) == 1

        # Should not be suppressed, name is different
        tmp = copy.copy(answer1)
        tmp.key = "testname3.local."
        tmp.name = "testname3.local."
        response.add_answer(query, tmp)
        assert len(response.answers) == 2

        # Should not be suppressed, type is different
        tmp = copy.copy(answer1)
        tmp.type = const._TYPE_A
        response.add_answer(query, tmp)
        assert len(response.answers) == 3

        # Should not be suppressed, class is different
        tmp = copy.copy(answer1)
        tmp.class_ = const._CLASS_NONE
        response.add_answer(query, tmp)
        assert len(response.answers) == 4

        # ::TODO:: could add additional tests for DNSAddress, DNSHinfo, DNSPointer, DNSText, DNSService

    def test_dns_hinfo(self):
        generated = r.DNSOutgoing(0)
        generated.add_additional_answer(DNSHinfo('irrelevant', const._TYPE_HINFO, 0, 0, 'cpu', 'os'))
        parsed = r.DNSIncoming(generated.packets()[0])
        answer = cast(r.DNSHinfo, parsed.answers()[0])
        assert answer.cpu == 'cpu'
        assert answer.os == 'os'

        generated = r.DNSOutgoing(0)
        generated.add_additional_answer(DNSHinfo('irrelevant', const._TYPE_HINFO, 0, 0, 'cpu', 'x' * 257))
        self.assertRaises(r.NamePartTooLongException, generated.packets)

    def test_many_questions(self):
        """Test many questions get seperated into multiple packets."""
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        questions = []
        for i in range(100):
            question = r.DNSQuestion(f"testname{i}.local.", const._TYPE_SRV, const._CLASS_IN)
            generated.add_question(question)
            questions.append(question)
        assert len(generated.questions) == 100

        packets = generated.packets()
        assert len(packets) == 2
        assert len(packets[0]) < const._MAX_MSG_TYPICAL
        assert len(packets[1]) < const._MAX_MSG_TYPICAL

        parsed1 = r.DNSIncoming(packets[0])
        assert len(parsed1.questions) == 85
        parsed2 = r.DNSIncoming(packets[1])
        assert len(parsed2.questions) == 15

    def test_many_questions_with_many_known_answers(self):
        """Test many questions and known answers get seperated into multiple packets."""
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        questions = []
        for _ in range(30):
            question = r.DNSQuestion("_hap._tcp.local.", const._TYPE_PTR, const._CLASS_IN)
            generated.add_question(question)
            questions.append(question)
        assert len(generated.questions) == 30
        now = current_time_millis()
        for _ in range(200):
            known_answer = r.DNSPointer(
                "myservice{i}_tcp._tcp.local.",
                const._TYPE_PTR,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_OTHER_TTL,
                '123.local.',
            )
            generated.add_answer_at_time(known_answer, now)
        packets = generated.packets()
        assert len(packets) == 3
        assert len(packets[0]) <= const._MAX_MSG_TYPICAL
        assert len(packets[1]) <= const._MAX_MSG_TYPICAL
        assert len(packets[2]) <= const._MAX_MSG_TYPICAL

        parsed1 = r.DNSIncoming(packets[0])
        assert len(parsed1.questions) == 30
        assert len(parsed1.answers()) == 88
        assert parsed1.truncated
        parsed2 = r.DNSIncoming(packets[1])
        assert len(parsed2.questions) == 0
        assert len(parsed2.answers()) == 101
        assert parsed2.truncated
        parsed3 = r.DNSIncoming(packets[2])
        assert len(parsed3.questions) == 0
        assert len(parsed3.answers()) == 11
        assert not parsed3.truncated

    def test_massive_probe_packet_split(self):
        """Test probe with many authorative answers."""
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY | const._FLAGS_AA)
        questions = []
        for _ in range(30):
            question = r.DNSQuestion(
                "_hap._tcp.local.", const._TYPE_PTR, const._CLASS_IN | const._CLASS_UNIQUE
            )
            generated.add_question(question)
            questions.append(question)
        assert len(generated.questions) == 30
        for _ in range(200):
            authorative_answer = r.DNSPointer(
                "myservice{i}_tcp._tcp.local.",
                const._TYPE_PTR,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_OTHER_TTL,
                '123.local.',
            )
            generated.add_authorative_answer(authorative_answer)
        packets = generated.packets()
        assert len(packets) == 3
        assert len(packets[0]) <= const._MAX_MSG_TYPICAL
        assert len(packets[1]) <= const._MAX_MSG_TYPICAL
        assert len(packets[2]) <= const._MAX_MSG_TYPICAL

        parsed1 = r.DNSIncoming(packets[0])
        assert parsed1.questions[0].unicast is True
        assert len(parsed1.questions) == 30
        assert parsed1.num_authorities == 88
        assert parsed1.truncated
        parsed2 = r.DNSIncoming(packets[1])
        assert len(parsed2.questions) == 0
        assert parsed2.num_authorities == 101
        assert parsed2.truncated
        parsed3 = r.DNSIncoming(packets[2])
        assert len(parsed3.questions) == 0
        assert parsed3.num_authorities == 11
        assert not parsed3.truncated

    def test_only_one_answer_can_by_large(self):
        """Test that only the first answer in each packet can be large.

        https://datatracker.ietf.org/doc/html/rfc6762#section-17
        """
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        query = r.DNSIncoming(r.DNSOutgoing(const._FLAGS_QR_QUERY).packets()[0])
        for i in range(3):
            generated.add_answer(
                query,
                r.DNSText(
                    "zoom._hap._tcp.local.",
                    const._TYPE_TXT,
                    const._CLASS_IN | const._CLASS_UNIQUE,
                    1200,
                    b'\x04ff=0\x04ci=2\x04sf=0\x0bsh=6fLM5A==' * 100,
                ),
            )
        generated.add_answer(
            query,
            r.DNSService(
                "testname1.local.",
                const._TYPE_SRV,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                0,
                0,
                80,
                "foo.local.",
            ),
        )
        assert len(generated.answers) == 4

        packets = generated.packets()
        assert len(packets) == 4
        assert len(packets[0]) <= const._MAX_MSG_ABSOLUTE
        assert len(packets[0]) > const._MAX_MSG_TYPICAL

        assert len(packets[1]) <= const._MAX_MSG_ABSOLUTE
        assert len(packets[1]) > const._MAX_MSG_TYPICAL

        assert len(packets[2]) <= const._MAX_MSG_ABSOLUTE
        assert len(packets[2]) > const._MAX_MSG_TYPICAL

        assert len(packets[3]) <= const._MAX_MSG_TYPICAL

        for packet in packets:
            parsed = r.DNSIncoming(packet)
            assert len(parsed.answers()) == 1

    def test_questions_do_not_end_up_every_packet(self):
        """Test that questions are not sent again when multiple packets are needed.

        https://datatracker.ietf.org/doc/html/rfc6762#section-7.2
        Sometimes a Multicast DNS querier will already have too many answers
        to fit in the Known-Answer Section of its query packets....  It MUST
        immediately follow the packet with another query packet containing no
        questions and as many more Known-Answer records as will fit.
        """

        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        for i in range(35):
            question = r.DNSQuestion(f"testname{i}.local.", const._TYPE_SRV, const._CLASS_IN)
            generated.add_question(question)
            answer = r.DNSService(
                f"testname{i}.local.",
                const._TYPE_SRV,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                0,
                0,
                80,
                f"foo{i}.local.",
            )
            generated.add_answer_at_time(answer, 0)

        assert len(generated.questions) == 35
        assert len(generated.answers) == 35

        packets = generated.packets()
        assert len(packets) == 2
        assert len(packets[0]) <= const._MAX_MSG_TYPICAL
        assert len(packets[1]) <= const._MAX_MSG_TYPICAL

        parsed1 = r.DNSIncoming(packets[0])
        assert len(parsed1.questions) == 35
        assert len(parsed1.answers()) == 33

        parsed2 = r.DNSIncoming(packets[1])
        assert len(parsed2.questions) == 0
        assert len(parsed2.answers()) == 2


class PacketForm(unittest.TestCase):
    def test_transaction_id(self):
        """ID must be zero in a DNS-SD packet"""
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        bytes = generated.packets()[0]
        id = bytes[0] << 8 | bytes[1]
        assert id == 0

    def test_setting_id(self):
        """Test setting id in the constructor"""
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY, id_=4444)
        assert generated.id == 4444

    def test_query_header_bits(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_QUERY)
        bytes = generated.packets()[0]
        flags = bytes[2] << 8 | bytes[3]
        assert flags == 0x0

    def test_response_header_bits(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        bytes = generated.packets()[0]
        flags = bytes[2] << 8 | bytes[3]
        assert flags == 0x8000

    def test_numbers(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        bytes = generated.packets()[0]
        (num_questions, num_answers, num_authorities, num_additionals) = struct.unpack('!4H', bytes[4:12])
        assert num_questions == 0
        assert num_answers == 0
        assert num_authorities == 0
        assert num_additionals == 0

    def test_numbers_questions(self):
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        question = r.DNSQuestion("testname.local.", const._TYPE_SRV, const._CLASS_IN)
        for i in range(10):
            generated.add_question(question)
        bytes = generated.packets()[0]
        (num_questions, num_answers, num_authorities, num_additionals) = struct.unpack('!4H', bytes[4:12])
        assert num_questions == 10
        assert num_answers == 0
        assert num_authorities == 0
        assert num_additionals == 0


class TestDnsIncoming(unittest.TestCase):
    def test_incoming_exception_handling(self):
        generated = r.DNSOutgoing(0)
        packet = generated.packets()[0]
        packet = packet[:8] + b'deadbeef' + packet[8:]
        parsed = r.DNSIncoming(packet)
        parsed = r.DNSIncoming(packet)
        assert parsed.valid is False

    def test_incoming_unknown_type(self):
        generated = r.DNSOutgoing(0)
        answer = r.DNSAddress('a', const._TYPE_SOA, const._CLASS_IN, 1, b'a')
        generated.add_additional_answer(answer)
        packet = generated.packets()[0]
        parsed = r.DNSIncoming(packet)
        assert len(parsed.answers()) == 0
        assert parsed.is_query() != parsed.is_response()

    def test_incoming_circular_reference(self):
        assert not r.DNSIncoming(
            bytes.fromhex(
                '01005e0000fb542a1bf0577608004500006897934000ff11d81bc0a86a31e00000fb'
                '14e914e90054f9b2000084000000000100000000095f7365727669636573075f646e'
                '732d7364045f756470056c6f63616c00000c0001000011940018105f73706f746966'
                '792d636f6e6e656374045f746370c023'
            )
        ).valid

    @unittest.skipIf(not has_working_ipv6(), 'Requires IPv6')
    @unittest.skipIf(os.environ.get('SKIP_IPV6'), 'IPv6 tests disabled')
    def test_incoming_ipv6(self):
        addr = "2606:2800:220:1:248:1893:25c8:1946"  # example.com
        packed = socket.inet_pton(socket.AF_INET6, addr)
        generated = r.DNSOutgoing(0)
        answer = r.DNSAddress('domain', const._TYPE_AAAA, const._CLASS_IN | const._CLASS_UNIQUE, 1, packed)
        generated.add_additional_answer(answer)
        packet = generated.packets()[0]
        parsed = r.DNSIncoming(packet)
        record = parsed.answers()[0]
        assert isinstance(record, r.DNSAddress)
        assert record.address == packed


def test_dns_compression_rollback_for_corruption():
    """Verify rolling back does not lead to dns compression corruption."""
    out = r.DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA)
    address = socket.inet_pton(socket.AF_INET, "192.168.208.5")

    additionals = [
        {
            "name": "HASS Bridge ZJWH FF5137._hap._tcp.local.",
            "address": address,
            "port": 51832,
            "text": b"\x13md=HASS Bridge"
            b" ZJWH\x06pv=1.0\x14id=01:6B:30:FF:51:37\x05c#=12\x04s#=1\x04ff=0\x04"
            b"ci=2\x04sf=0\x0bsh=L0m/aQ==",
        },
        {
            "name": "HASS Bridge 3K9A C2582A._hap._tcp.local.",
            "address": address,
            "port": 51834,
            "text": b"\x13md=HASS Bridge"
            b" 3K9A\x06pv=1.0\x14id=E2:AA:5B:C2:58:2A\x05c#=12\x04s#=1\x04ff=0\x04"
            b"ci=2\x04sf=0\x0bsh=b2CnzQ==",
        },
        {
            "name": "Master Bed TV CEDB27._hap._tcp.local.",
            "address": address,
            "port": 51830,
            "text": b"\x10md=Master Bed"
            b" TV\x06pv=1.0\x14id=9E:B7:44:CE:DB:27\x05c#=18\x04s#=1\x04ff=0\x05"
            b"ci=31\x04sf=0\x0bsh=CVj1kw==",
        },
        {
            "name": "Living Room TV 921B77._hap._tcp.local.",
            "address": address,
            "port": 51833,
            "text": b"\x11md=Living Room"
            b" TV\x06pv=1.0\x14id=11:61:E7:92:1B:77\x05c#=17\x04s#=1\x04ff=0\x05"
            b"ci=31\x04sf=0\x0bsh=qU77SQ==",
        },
        {
            "name": "HASS Bridge ZC8X FF413D._hap._tcp.local.",
            "address": address,
            "port": 51829,
            "text": b"\x13md=HASS Bridge"
            b" ZC8X\x06pv=1.0\x14id=96:14:45:FF:41:3D\x05c#=12\x04s#=1\x04ff=0\x04"
            b"ci=2\x04sf=0\x0bsh=b0QZlg==",
        },
        {
            "name": "HASS Bridge WLTF 4BE61F._hap._tcp.local.",
            "address": address,
            "port": 51837,
            "text": b"\x13md=HASS Bridge"
            b" WLTF\x06pv=1.0\x14id=E0:E7:98:4B:E6:1F\x04c#=2\x04s#=1\x04ff=0\x04"
            b"ci=2\x04sf=0\x0bsh=ahAISA==",
        },
        {
            "name": "FrontdoorCamera 8941D1._hap._tcp.local.",
            "address": address,
            "port": 54898,
            "text": b"\x12md=FrontdoorCamera\x06pv=1.0\x14id=9F:B7:DC:89:41:D1\x04c#=2\x04"
            b"s#=1\x04ff=0\x04ci=2\x04sf=0\x0bsh=0+MXmA==",
        },
        {
            "name": "HASS Bridge W9DN 5B5CC5._hap._tcp.local.",
            "address": address,
            "port": 51836,
            "text": b"\x13md=HASS Bridge"
            b" W9DN\x06pv=1.0\x14id=11:8E:DB:5B:5C:C5\x05c#=12\x04s#=1\x04ff=0\x04"
            b"ci=2\x04sf=0\x0bsh=6fLM5A==",
        },
        {
            "name": "HASS Bridge Y9OO EFF0A7._hap._tcp.local.",
            "address": address,
            "port": 51838,
            "text": b"\x13md=HASS Bridge"
            b" Y9OO\x06pv=1.0\x14id=D3:FE:98:EF:F0:A7\x04c#=2\x04s#=1\x04ff=0\x04"
            b"ci=2\x04sf=0\x0bsh=u3bdfw==",
        },
        {
            "name": "Snooze Room TV 6B89B0._hap._tcp.local.",
            "address": address,
            "port": 51835,
            "text": b"\x11md=Snooze Room"
            b" TV\x06pv=1.0\x14id=5F:D5:70:6B:89:B0\x05c#=17\x04s#=1\x04ff=0\x05"
            b"ci=31\x04sf=0\x0bsh=xNTqsg==",
        },
        {
            "name": "AlexanderHomeAssistant 74651D._hap._tcp.local.",
            "address": address,
            "port": 54811,
            "text": b"\x19md=AlexanderHomeAssistant\x06pv=1.0\x14id=59:8A:0B:74:65:1D\x05"
            b"c#=14\x04s#=1\x04ff=0\x04ci=2\x04sf=0\x0bsh=ccZLPA==",
        },
        {
            "name": "HASS Bridge OS95 39C053._hap._tcp.local.",
            "address": address,
            "port": 51831,
            "text": b"\x13md=HASS Bridge"
            b" OS95\x06pv=1.0\x14id=7E:8C:E6:39:C0:53\x05c#=12\x04s#=1\x04ff=0\x04ci=2"
            b"\x04sf=0\x0bsh=Xfe5LQ==",
        },
    ]

    out.add_answer_at_time(
        DNSText(
            "HASS Bridge W9DN 5B5CC5._hap._tcp.local.",
            const._TYPE_TXT,
            const._CLASS_IN | const._CLASS_UNIQUE,
            const._DNS_OTHER_TTL,
            b'\x13md=HASS Bridge W9DN\x06pv=1.0\x14id=11:8E:DB:5B:5C:C5\x05c#=12\x04s#=1'
            b'\x04ff=0\x04ci=2\x04sf=0\x0bsh=6fLM5A==',
        ),
        0,
    )

    for record in additionals:
        out.add_additional_answer(
            r.DNSService(
                record["name"],  # type: ignore
                const._TYPE_SRV,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                0,
                0,
                record["port"],  # type: ignore
                record["name"],  # type: ignore
            )
        )
        out.add_additional_answer(
            r.DNSText(
                record["name"],  # type: ignore
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_OTHER_TTL,
                record["text"],  # type: ignore
            )
        )
        out.add_additional_answer(
            r.DNSAddress(
                record["name"],  # type: ignore
                const._TYPE_A,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                record["address"],  # type: ignore
            )
        )

    for packet in out.packets():
        # Verify we can process the packets we created to
        # ensure there is no corruption with the dns compression
        incoming = r.DNSIncoming(packet)
        assert incoming.valid is True
        assert (
            len(incoming.answers())
            == incoming.num_answers + incoming.num_authorities + incoming.num_additionals
        )


def test_tc_bit_in_query_packet():
    """Verify the TC bit is set when known answers exceed the packet size."""
    out = r.DNSOutgoing(const._FLAGS_QR_QUERY | const._FLAGS_AA)
    type_ = "_hap._tcp.local."
    out.add_question(r.DNSQuestion(type_, const._TYPE_PTR, const._CLASS_IN))

    for i in range(30):
        out.add_answer_at_time(
            DNSText(
                ("HASS Bridge W9DN %s._hap._tcp.local." % i),
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_OTHER_TTL,
                b'\x13md=HASS Bridge W9DN\x06pv=1.0\x14id=11:8E:DB:5B:5C:C5\x05c#=12\x04s#=1'
                b'\x04ff=0\x04ci=2\x04sf=0\x0bsh=6fLM5A==',
            ),
            0,
        )

    packets = out.packets()
    assert len(packets) == 3

    first_packet = r.DNSIncoming(packets[0])
    assert first_packet.truncated
    assert first_packet.valid is True

    second_packet = r.DNSIncoming(packets[1])
    assert second_packet.truncated
    assert second_packet.valid is True

    third_packet = r.DNSIncoming(packets[2])
    assert not third_packet.truncated
    assert third_packet.valid is True


def test_tc_bit_not_set_in_answer_packet():
    """Verify the TC bit is not set when there are no questions and answers exceed the packet size."""
    out = r.DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA)
    for i in range(30):
        out.add_answer_at_time(
            DNSText(
                ("HASS Bridge W9DN %s._hap._tcp.local." % i),
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_OTHER_TTL,
                b'\x13md=HASS Bridge W9DN\x06pv=1.0\x14id=11:8E:DB:5B:5C:C5\x05c#=12\x04s#=1'
                b'\x04ff=0\x04ci=2\x04sf=0\x0bsh=6fLM5A==',
            ),
            0,
        )

    packets = out.packets()
    assert len(packets) == 3

    first_packet = r.DNSIncoming(packets[0])
    assert not first_packet.truncated
    assert first_packet.valid is True

    second_packet = r.DNSIncoming(packets[1])
    assert not second_packet.truncated
    assert second_packet.valid is True

    third_packet = r.DNSIncoming(packets[2])
    assert not third_packet.truncated
    assert third_packet.valid is True


# 4003	15.973052	192.168.107.68	224.0.0.251	MDNS	76	Standard query 0xffc4 PTR _raop._tcp.local, "QM" question
def test_qm_packet_parser():
    """Test we can parse a query packet with the QM bit."""
    qm_packet = (
        b'\xff\xc4\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x05_raop\x04_tcp\x05local\x00\x00\x0c\x00\x01'
    )
    parsed = DNSIncoming(qm_packet)
    assert parsed.questions[0].unicast is False
    assert ",QM," in str(parsed.questions[0])


# 389951	1450.577370	192.168.107.111	224.0.0.251	MDNS	115	Standard query 0x0000 PTR _companion-link._tcp.local, "QU" question OPT
def test_qu_packet_parser():
    """Test we can parse a query packet with the QU bit."""
    qu_packet = (
        b'\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x01\x0f_companion-link\x04_tcp\x05local'
        b'\x00\x00\x0c\x80\x01\x00\x00)\x05\xa0\x00\x00\x11\x94\x00\x12\x00\x04\x00\x0e\x00dz{\x8a6\x9czF\x84,\xcaQ\xff'
    )
    parsed = DNSIncoming(qu_packet)
    assert parsed.questions[0].unicast is True
    assert ",QU," in str(parsed.questions[0])


def test_parse_packet_with_nsec_record():
    """Test we can parse a packet with an NSEC record."""
    nsec_packet = (
        b"\x00\x00\x84\x00\x00\x00\x00\x01\x00\x00\x00\x03\x08_meshcop\x04_udp\x05local\x00\x00\x0c\x00"
        b"\x01\x00\x00\x11\x94\x00\x0f\x0cMyHome54 (2)\xc0\x0c\xc0+\x00\x10\x80\x01\x00\x00\x11\x94\x00"
        b")\x0bnn=MyHome54\x13xp=695034D148CC4784\x08tv=0.0.0\xc0+\x00!\x80\x01\x00\x00\x00x\x00\x15\x00"
        b"\x00\x00\x00\xc0'\x0cMaster-Bed-2\xc0\x1a\xc0+\x00/\x80\x01\x00\x00\x11\x94\x00\t\xc0+\x00\x05"
        b"\x00\x00\x80\x00@"
    )
    parsed = DNSIncoming(nsec_packet)
    nsec_record = cast(r.DNSNsec, parsed.answers()[3])
    assert "nsec," in str(nsec_record)
    assert nsec_record.rdtypes == [16, 33]
    assert nsec_record.next_name == "MyHome54 (2)._meshcop._udp.local."


def test_records_same_packet_share_fate():
    """Test records in the same packet all have the same created time."""
    out = r.DNSOutgoing(const._FLAGS_QR_QUERY | const._FLAGS_AA)
    type_ = "_hap._tcp.local."
    out.add_question(r.DNSQuestion(type_, const._TYPE_PTR, const._CLASS_IN))

    for i in range(30):
        out.add_answer_at_time(
            DNSText(
                ("HASS Bridge W9DN %s._hap._tcp.local." % i),
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_OTHER_TTL,
                b'\x13md=HASS Bridge W9DN\x06pv=1.0\x14id=11:8E:DB:5B:5C:C5\x05c#=12\x04s#=1'
                b'\x04ff=0\x04ci=2\x04sf=0\x0bsh=6fLM5A==',
            ),
            0,
        )

    for packet in out.packets():
        dnsin = DNSIncoming(packet)
        first_time = dnsin.answers()[0].created
        for answer in dnsin.answers():
            assert answer.created == first_time


def test_dns_compression_invalid_skips_bad_name_compress_in_question():
    """Test our wire parser can skip bad compression in questions."""
    packet = (
        b'\x00\x00\x00\x00\x00\x04\x00\x00\x00\x07\x00\x00\x11homeassistant1128\x05l'
        b'ocal\x00\x00\xff\x00\x014homeassistant1128 [534a4794e5ed41879ecf012252d3e02'
        b'a]\x0c_workstation\x04_tcp\xc0\x1e\x00\xff\x00\x014homeassistant1127 [534a47'
        b'94e5ed41879ecf012252d3e02a]\xc0^\x00\xff\x00\x014homeassistant1123 [534a479'
        b'4e5ed41879ecf012252d3e02a]\xc0^\x00\xff\x00\x014homeassistant1118 [534a4794'
        b'e5ed41879ecf012252d3e02a]\xc0^\x00\xff\x00\x01\xc0\x0c\x00\x01\x80'
        b'\x01\x00\x00\x00x\x00\x04\xc0\xa8<\xc3\xc0v\x00\x10\x80\x01\x00\x00\x00'
        b'x\x00\x01\x00\xc0v\x00!\x80\x01\x00\x00\x00x\x00\x1f\x00\x00\x00\x00'
        b'\x00\x00\x11homeassistant1127\x05local\x00\xc0\xb1\x00\x10\x80'
        b'\x01\x00\x00\x00x\x00\x01\x00\xc0\xb1\x00!\x80\x01\x00\x00\x00x\x00\x1f'
        b'\x00\x00\x00\x00\x00\x00\x11homeassistant1123\x05local\x00\xc0)\x00\x10\x80'
        b'\x01\x00\x00\x00x\x00\x01\x00\xc0)\x00!\x80\x01\x00\x00\x00x\x00\x1f'
        b'\x00\x00\x00\x00\x00\x00\x11homeassistant1128\x05local\x00'
    )
    parsed = r.DNSIncoming(packet)
    assert len(parsed.questions) == 4


def test_dns_compression_all_invalid(caplog):
    """Test our wire parser can skip all invalid data."""
    packet = (
        b'\x00\x00\x84\x00\x00\x00\x00\x01\x00\x00\x00\x00!roborock-vacuum-s5e_miio416'
        b'112328\x00\x00/\x80\x01\x00\x00\x00x\x00\t\xc0P\x00\x05@\x00\x00\x00\x00'
    )
    parsed = r.DNSIncoming(packet, ("2.4.5.4", 5353))
    assert len(parsed.questions) == 0
    assert len(parsed.answers()) == 0

    assert " Unable to parse; skipping record" in caplog.text


def test_invalid_next_name_ignored():
    """Test our wire parser does not throw an an invalid next name.

    The RFC states it should be ignored when used with mDNS.
    """
    packet = (
        b'\x00\x00\x00\x00\x00\x01\x00\x02\x00\x00\x00\x00\x07Android\x05local\x00\x00'
        b'\xff\x00\x01\xc0\x0c\x00/\x00\x01\x00\x00\x00x\x00\x08\xc02\x00\x04@'
        b'\x00\x00\x08\xc0\x0c\x00\x01\x00\x01\x00\x00\x00x\x00\x04\xc0\xa8X<'
    )
    parsed = r.DNSIncoming(packet)
    assert len(parsed.questions) == 1
    assert len(parsed.answers()) == 2


def test_dns_compression_invalid_skips_record():
    """Test our wire parser can skip records we do not know how to parse."""
    packet = (
        b"\x00\x00\x84\x00\x00\x00\x00\x06\x00\x00\x00\x00\x04_hap\x04_tcp\x05local\x00\x00\x0c"
        b"\x00\x01\x00\x00\x11\x94\x00\x16\x13eufy HomeBase2-2464\xc0\x0c\x04Eufy\xc0\x16\x00/"
        b"\x80\x01\x00\x00\x00x\x00\x08\xc0\xa6\x00\x04@\x00\x00\x08\xc0'\x00/\x80\x01\x00\x00"
        b"\x11\x94\x00\t\xc0'\x00\x05\x00\x00\x80\x00@\xc0=\x00\x01\x80\x01\x00\x00\x00x\x00\x04"
        b"\xc0\xa8Dp\xc0'\x00!\x80\x01\x00\x00\x00x\x00\x08\x00\x00\x00\x00\xd1_\xc0=\xc0'\x00"
        b"\x10\x80\x01\x00\x00\x11\x94\x00K\x04c#=1\x04ff=2\x14id=38:71:4F:6B:76:00\x08md=T8010"
        b"\x06pv=1.1\x05s#=75\x04sf=1\x04ci=2\x0bsh=xaQk4g=="
    )
    parsed = r.DNSIncoming(packet)
    answer = r.DNSNsec(
        'eufy HomeBase2-2464._hap._tcp.local.',
        const._TYPE_NSEC,
        const._CLASS_IN | const._CLASS_UNIQUE,
        const._DNS_OTHER_TTL,
        'eufy HomeBase2-2464._hap._tcp.local.',
        [const._TYPE_TXT, const._TYPE_SRV],
    )
    assert answer in parsed.answers()


def test_dns_compression_points_forward():
    """Test our wire parser can unpack nsec records with compression."""
    packet = (
        b"\x00\x00\x84\x00\x00\x00\x00\x07\x00\x00\x00\x00\x0eTV Beneden (2)"
        b"\x10_androidtvremote\x04_tcp\x05local\x00\x00\x10\x80\x01\x00\x00\x11"
        b"\x94\x00\x15\x14bt=D8:13:99:AC:98:F1\xc0\x0c\x00/\x80\x01\x00\x00\x11"
        b"\x94\x00\t\xc0\x0c\x00\x05\x00\x00\x80\x00@\tAndroid-3\xc01\x00/\x80"
        b"\x01\x00\x00\x00x\x00\x08\xc0\x9c\x00\x04@\x00\x00\x08\xc0l\x00\x01\x80"
        b"\x01\x00\x00\x00x\x00\x04\xc0\xa8X\x0f\xc0\x0c\x00!\x80\x01\x00\x00\x00"
        b"x\x00\x08\x00\x00\x00\x00\x19B\xc0l\xc0\x1b\x00\x0c\x00\x01\x00\x00\x11"
        b"\x94\x00\x02\xc0\x0c\t_services\x07_dns-sd\x04_udp\xc01\x00\x0c\x00\x01"
        b"\x00\x00\x11\x94\x00\x02\xc0\x1b"
    )
    parsed = r.DNSIncoming(packet)
    answer = r.DNSNsec(
        'TV Beneden (2)._androidtvremote._tcp.local.',
        const._TYPE_NSEC,
        const._CLASS_IN | const._CLASS_UNIQUE,
        const._DNS_OTHER_TTL,
        'TV Beneden (2)._androidtvremote._tcp.local.',
        [const._TYPE_TXT, const._TYPE_SRV],
    )
    assert answer in parsed.answers()


def test_dns_compression_points_to_itself():
    """Test our wire parser does not loop forever when a compression pointer points to itself."""
    packet = (
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x06domain\x05local\x00\x00\x01"
        b"\x80\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x05\xc0(\x00\x01\x80\x01\x00\x00\x00"
        b"\x01\x00\x04\xc0\xa8\xd0\x06"
    )
    parsed = r.DNSIncoming(packet)
    assert len(parsed.answers()) == 1


def test_dns_compression_points_beyond_packet():
    """Test our wire parser does not fail when the compression pointer points beyond the packet."""
    packet = (
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x06domain\x05local\x00\x00\x01'
        b'\x80\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x05\xe7\x0f\x00\x01\x80\x01\x00\x00'
        b'\x00\x01\x00\x04\xc0\xa8\xd0\x06'
    )
    parsed = r.DNSIncoming(packet)
    assert len(parsed.answers()) == 1


def test_dns_compression_generic_failure(caplog):
    """Test our wire parser does not loop forever when dns compression is corrupt."""
    packet = (
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x06domain\x05local\x00\x00\x01'
        b'\x80\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x05-\x0c\x00\x01\x80\x01\x00\x00'
        b'\x00\x01\x00\x04\xc0\xa8\xd0\x06'
    )
    parsed = r.DNSIncoming(packet, ("1.2.3.4", 5353))
    assert len(parsed.answers()) == 1
    assert "Received invalid packet from ('1.2.3.4', 5353)" in caplog.text


def test_label_length_attack():
    """Test our wire parser does not loop forever when the name exceeds 253 chars."""
    packet = (
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d'
        b'\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x01d\x00\x00\x01\x80'
        b'\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x05\xc0\x0c\x00\x01\x80\x01\x00\x00\x00'
        b'\x01\x00\x04\xc0\xa8\xd0\x06'
    )
    parsed = r.DNSIncoming(packet)
    assert len(parsed.answers()) == 0


def test_label_compression_attack():
    """Test our wire parser does not loop forever when exceeding the maximum number of labels."""
    packet = (
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x03atk\x00\x00\x01\x80'
        b'\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x05\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03'
        b'atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\x03atk\xc0'
        b'\x0c\x00\x01\x80\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x06'
    )
    parsed = r.DNSIncoming(packet)
    assert len(parsed.answers()) == 1


def test_dns_compression_loop_attack():
    """Test our wire parser does not loop forever when dns compression is in a loop."""
    packet = (
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x03atk\x03dns\x05loc'
        b'al\xc0\x10\x00\x01\x80\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x05\x04a'
        b'tk2\x04dns2\xc0\x14\x00\x01\x80\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0\x05'
        b'\x04atk3\xc0\x10\x00\x01\x80\x01\x00\x00\x00\x01\x00\x04\xc0\xa8\xd0'
        b'\x05\x04atk4\x04dns5\xc0\x14\x00\x01\x80\x01\x00\x00\x00\x01\x00\x04\xc0'
        b'\xa8\xd0\x05\x04atk5\x04dns2\xc0^\x00\x01\x80\x01\x00\x00\x00\x01\x00'
        b'\x04\xc0\xa8\xd0\x05\xc0s\x00\x01\x80\x01\x00\x00\x00\x01\x00'
        b'\x04\xc0\xa8\xd0\x05\xc0s\x00\x01\x80\x01\x00\x00\x00\x01\x00'
        b'\x04\xc0\xa8\xd0\x05'
    )
    parsed = r.DNSIncoming(packet)
    assert len(parsed.answers()) == 0


def test_txt_after_invalid_nsec_name_still_usable():
    """Test that we can see the txt record after the invalid nsec record."""
    packet = (
        b'\x00\x00\x84\x00\x00\x00\x00\x06\x00\x00\x00\x00\x06_sonos\x04_tcp\x05loc'
        b'al\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00\x15\x12Sonos-542A1BC9220E'
        b'\xc0\x0c\x12Sonos-542A1BC9220E\xc0\x18\x00/\x80\x01\x00\x00\x00x\x00'
        b'\x08\xc1t\x00\x04@\x00\x00\x08\xc0)\x00/\x80\x01\x00\x00\x11\x94\x00'
        b'\t\xc0)\x00\x05\x00\x00\x80\x00@\xc0)\x00!\x80\x01\x00\x00\x00x'
        b'\x00\x08\x00\x00\x00\x00\x05\xa3\xc0>\xc0>\x00\x01\x80\x01\x00\x00\x00x'
        b'\x00\x04\xc0\xa8\x02:\xc0)\x00\x10\x80\x01\x00\x00\x11\x94\x01*2info=/api'
        b'/v1/players/RINCON_542A1BC9220E01400/info\x06vers=3\x10protovers=1.24.1\nbo'
        b'otseq=11%hhid=Sonos_rYn9K9DLXJe0f3LP9747lbvFvh;mhhid=Sonos_rYn9K9DLXJe0f3LP9'
        b'747lbvFvh.Q45RuMaeC07rfXh7OJGm<location=http://192.168.2.58:1400/xml/device_'
        b'description.xml\x0csslport=1443\x0ehhsslport=1843\tvariant=2\x0emdnssequen'
        b'ce=0'
    )
    parsed = r.DNSIncoming(packet)
    txt_record = cast(r.DNSText, parsed.answers()[4])
    # The NSEC record with the invalid name compression should be skipped
    assert txt_record.text == (
        b'2info=/api/v1/players/RINCON_542A1BC9220E01400/info\x06vers=3\x10protovers'
        b'=1.24.1\nbootseq=11%hhid=Sonos_rYn9K9DLXJe0f3LP9747lbvFvh;mhhid=Sonos_rYn'
        b'9K9DLXJe0f3LP9747lbvFvh.Q45RuMaeC07rfXh7OJGm<location=http://192.168.2.58:14'
        b'00/xml/device_description.xml\x0csslport=1443\x0ehhsslport=1843\tvarian'
        b't=2\x0emdnssequence=0'
    )
    assert len(parsed.answers()) == 5
