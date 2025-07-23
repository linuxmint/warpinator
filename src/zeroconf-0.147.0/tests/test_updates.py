"""Unit tests for zeroconf._updates."""

from __future__ import annotations

import logging
import socket
import time

import pytest

import zeroconf as r
from zeroconf import Zeroconf, const
from zeroconf._record_update import RecordUpdate
from zeroconf._services.browser import ServiceBrowser
from zeroconf._services.info import ServiceInfo

log = logging.getLogger("zeroconf")
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


def test_legacy_record_update_listener():
    """Test a RecordUpdateListener that does not implement update_records."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=["127.0.0.1"])

    with pytest.raises(RuntimeError):
        r.RecordUpdateListener().update_record(
            zc,
            0,
            r.DNSRecord("irrelevant", const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL),
        )

    updates = []

    class LegacyRecordUpdateListener(r.RecordUpdateListener):
        """A RecordUpdateListener that does not implement update_records."""

        def update_record(self, zc: Zeroconf, now: float, record: r.DNSRecord) -> None:
            updates.append(record)

    listener = LegacyRecordUpdateListener()

    zc.add_listener(listener, None)

    # dummy service callback
    def on_service_state_change(zeroconf, service_type, state_change, name):
        pass

    # start a browser
    type_ = "_homeassistant._tcp.local."
    name = "MyTestHome"
    browser = ServiceBrowser(zc, type_, [on_service_state_change])

    info_service = ServiceInfo(
        type_,
        f"{name}.{type_}",
        80,
        0,
        0,
        {"path": "/~paulsm/"},
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )

    zc.register_service(info_service)

    time.sleep(0.001)

    browser.cancel()

    assert updates
    assert len([isinstance(update, r.DNSPointer) and update.name == type_ for update in updates]) >= 1

    zc.remove_listener(listener)
    # Removing a second time should not throw
    zc.remove_listener(listener)

    zc.close()


def test_record_update_compat():
    """Test a RecordUpdate can fetch by index."""
    new = r.DNSPointer("irrelevant", const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, "new")
    old = r.DNSPointer("irrelevant", const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL, "old")
    update = RecordUpdate(new, old)
    assert update[0] == new
    assert update[1] == old
    with pytest.raises(IndexError):
        update[2]
    assert update.new == new
    assert update.old == old
