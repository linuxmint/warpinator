"""Benchmark helpers."""

from __future__ import annotations

import socket

from zeroconf import DNSAddress, DNSOutgoing, DNSService, DNSText, const


def generate_packets() -> DNSOutgoing:
    out = DNSOutgoing(const._FLAGS_QR_RESPONSE | const._FLAGS_AA)
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
            b"\x13md=HASS Bridge W9DN\x06pv=1.0\x14id=11:8E:DB:5B:5C:C5\x05c#=12\x04s#=1"
            b"\x04ff=0\x04ci=2\x04sf=0\x0bsh=6fLM5A==",
        ),
        0,
    )

    for record in additionals:
        out.add_additional_answer(
            DNSService(
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
            DNSText(
                record["name"],  # type: ignore
                const._TYPE_TXT,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_OTHER_TTL,
                record["text"],  # type: ignore
            )
        )
        out.add_additional_answer(
            DNSAddress(
                record["name"],  # type: ignore
                const._TYPE_A,
                const._CLASS_IN | const._CLASS_UNIQUE,
                const._DNS_HOST_TTL,
                record["address"],  # type: ignore
            )
        )

    return out
