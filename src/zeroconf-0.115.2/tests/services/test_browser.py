#!/usr/bin/env python


""" Unit tests for zeroconf._services.browser. """

import asyncio
import logging
import os
import socket
import time
import unittest
from threading import Event
from typing import Iterable, Set, cast
from unittest.mock import patch

import pytest

import zeroconf as r
import zeroconf._services.browser as _services_browser
from zeroconf import (
    DNSPointer,
    DNSQuestion,
    Zeroconf,
    _engine,
    const,
    current_time_millis,
    millis_to_seconds,
)
from zeroconf._handlers import record_manager
from zeroconf._services import ServiceStateChange
from zeroconf._services.browser import ServiceBrowser
from zeroconf._services.info import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from .. import (
    QuestionHistoryWithoutSuppression,
    _inject_response,
    _wait_for_start,
    has_working_ipv6,
)

log = logging.getLogger('zeroconf')
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


def test_service_browser_cancel_multiple_times():
    """Test we can cancel a ServiceBrowser multiple times before close."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_hap._tcp.local."

    class MyServiceListener(r.ServiceListener):
        pass

    listener = MyServiceListener()

    browser = r.ServiceBrowser(zc, type_, None, listener)

    browser.cancel()
    browser.cancel()
    browser.cancel()

    zc.close()


def test_service_browser_cancel_context_manager():
    """Test we can cancel a ServiceBrowser with it being used as a context manager."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_hap._tcp.local."

    class MyServiceListener(r.ServiceListener):
        pass

    listener = MyServiceListener()

    browser = r.ServiceBrowser(zc, type_, None, listener)

    assert cast(bool, browser.done) is False

    with browser:
        pass

    # ensure call_soon_threadsafe in ServiceBrowser.cancel is run
    assert zc.loop is not None
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0), zc.loop).result()

    assert cast(bool, browser.done) is True

    zc.close()


def test_service_browser_cancel_multiple_times_after_close():
    """Test we can cancel a ServiceBrowser multiple times after close."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_hap._tcp.local."

    class MyServiceListener(r.ServiceListener):
        pass

    listener = MyServiceListener()

    browser = r.ServiceBrowser(zc, type_, None, listener)

    zc.close()

    browser.cancel()
    browser.cancel()
    browser.cancel()


def test_service_browser_started_after_zeroconf_closed():
    """Test starting a ServiceBrowser after close raises RuntimeError."""
    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_hap._tcp.local."

    class MyServiceListener(r.ServiceListener):
        pass

    listener = MyServiceListener()
    zc.close()

    with pytest.raises(RuntimeError):
        r.ServiceBrowser(zc, type_, None, listener)


def test_multiple_instances_running_close():
    """Test we can shutdown multiple instances."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    zc2 = Zeroconf(interfaces=['127.0.0.1'])
    zc3 = Zeroconf(interfaces=['127.0.0.1'])

    assert zc.loop != zc2.loop
    assert zc.loop != zc3.loop

    class MyServiceListener(r.ServiceListener):
        pass

    listener = MyServiceListener()

    zc2.add_service_listener("zca._hap._tcp.local.", listener)

    zc.close()
    zc2.remove_service_listener(listener)
    zc2.close()
    zc3.close()


class TestServiceBrowser(unittest.TestCase):
    def test_update_record(self):
        enable_ipv6 = has_working_ipv6() and not os.environ.get('SKIP_IPV6')

        service_name = 'name._type._tcp.local.'
        service_type = '_type._tcp.local.'
        service_server = 'ash-1.local.'
        service_text = b'path=/~matt1/'
        service_address = '10.0.1.2'
        service_v6_address = "2001:db8::1"
        service_v6_second_address = "6001:db8::1"

        service_added_count = 0
        service_removed_count = 0
        service_updated_count = 0
        service_add_event = Event()
        service_removed_event = Event()
        service_updated_event = Event()

        class MyServiceListener(r.ServiceListener):
            def add_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
                nonlocal service_added_count
                service_added_count += 1
                service_add_event.set()

            def remove_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
                nonlocal service_removed_count
                service_removed_count += 1
                service_removed_event.set()

            def update_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
                nonlocal service_updated_count
                service_updated_count += 1
                service_info = zc.get_service_info(type_, name)
                assert socket.inet_aton(service_address) in service_info.addresses
                if enable_ipv6:
                    assert socket.inet_pton(
                        socket.AF_INET6, service_v6_address
                    ) in service_info.addresses_by_version(r.IPVersion.V6Only)
                    assert socket.inet_pton(
                        socket.AF_INET6, service_v6_second_address
                    ) in service_info.addresses_by_version(r.IPVersion.V6Only)
                assert service_info.text == service_text
                assert service_info.server.lower() == service_server.lower()
                service_updated_event.set()

        def mock_incoming_msg(service_state_change: r.ServiceStateChange) -> r.DNSIncoming:
            generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
            assert generated.is_response() is True

            if service_state_change == r.ServiceStateChange.Removed:
                ttl = 0
            else:
                ttl = 120

            generated.add_answer_at_time(
                r.DNSText(
                    service_name, const._TYPE_TXT, const._CLASS_IN | const._CLASS_UNIQUE, ttl, service_text
                ),
                0,
            )

            generated.add_answer_at_time(
                r.DNSService(
                    service_name,
                    const._TYPE_SRV,
                    const._CLASS_IN | const._CLASS_UNIQUE,
                    ttl,
                    0,
                    0,
                    80,
                    service_server,
                ),
                0,
            )

            # Send the IPv6 address first since we previously
            # had a bug where the IPv4 would be missing if the
            # IPv6 was seen first
            if enable_ipv6:
                generated.add_answer_at_time(
                    r.DNSAddress(
                        service_server,
                        const._TYPE_AAAA,
                        const._CLASS_IN | const._CLASS_UNIQUE,
                        ttl,
                        socket.inet_pton(socket.AF_INET6, service_v6_address),
                    ),
                    0,
                )
                generated.add_answer_at_time(
                    r.DNSAddress(
                        service_server,
                        const._TYPE_AAAA,
                        const._CLASS_IN | const._CLASS_UNIQUE,
                        ttl,
                        socket.inet_pton(socket.AF_INET6, service_v6_second_address),
                    ),
                    0,
                )
            generated.add_answer_at_time(
                r.DNSAddress(
                    service_server,
                    const._TYPE_A,
                    const._CLASS_IN | const._CLASS_UNIQUE,
                    ttl,
                    socket.inet_aton(service_address),
                ),
                0,
            )

            generated.add_answer_at_time(
                r.DNSPointer(service_type, const._TYPE_PTR, const._CLASS_IN, ttl, service_name), 0
            )

            return r.DNSIncoming(generated.packets()[0])

        zeroconf = r.Zeroconf(interfaces=['127.0.0.1'])
        service_browser = r.ServiceBrowser(zeroconf, service_type, listener=MyServiceListener())

        try:
            wait_time = 3

            # service added
            _inject_response(zeroconf, mock_incoming_msg(r.ServiceStateChange.Added))
            service_add_event.wait(wait_time)
            assert service_added_count == 1
            assert service_updated_count == 0
            assert service_removed_count == 0

            # service SRV updated
            service_updated_event.clear()
            service_server = 'ash-2.local.'
            _inject_response(zeroconf, mock_incoming_msg(r.ServiceStateChange.Updated))
            service_updated_event.wait(wait_time)
            assert service_added_count == 1
            assert service_updated_count == 1
            assert service_removed_count == 0

            # service TXT updated
            service_updated_event.clear()
            service_text = b'path=/~matt2/'
            _inject_response(zeroconf, mock_incoming_msg(r.ServiceStateChange.Updated))
            service_updated_event.wait(wait_time)
            assert service_added_count == 1
            assert service_updated_count == 2
            assert service_removed_count == 0

            # service TXT updated - duplicate update should not trigger another service_updated
            service_updated_event.clear()
            service_text = b'path=/~matt2/'
            _inject_response(zeroconf, mock_incoming_msg(r.ServiceStateChange.Updated))
            service_updated_event.wait(wait_time)
            assert service_added_count == 1
            assert service_updated_count == 2
            assert service_removed_count == 0

            # service A updated
            service_updated_event.clear()
            service_address = '10.0.1.3'
            # Verify we match on uppercase
            service_server = service_server.upper()
            _inject_response(zeroconf, mock_incoming_msg(r.ServiceStateChange.Updated))
            service_updated_event.wait(wait_time)
            assert service_added_count == 1
            assert service_updated_count == 3
            assert service_removed_count == 0

            # service all updated
            service_updated_event.clear()
            service_server = 'ash-3.local.'
            service_text = b'path=/~matt3/'
            service_address = '10.0.1.3'
            _inject_response(zeroconf, mock_incoming_msg(r.ServiceStateChange.Updated))
            service_updated_event.wait(wait_time)
            assert service_added_count == 1
            assert service_updated_count == 4
            assert service_removed_count == 0

            # service removed
            _inject_response(zeroconf, mock_incoming_msg(r.ServiceStateChange.Removed))
            service_removed_event.wait(wait_time)
            assert service_added_count == 1
            assert service_updated_count == 4
            assert service_removed_count == 1

        finally:
            assert len(zeroconf.listeners) == 1
            service_browser.cancel()
            time.sleep(0.2)
            assert len(zeroconf.listeners) == 0
            zeroconf.remove_all_service_listeners()
            zeroconf.close()


class TestServiceBrowserMultipleTypes(unittest.TestCase):
    def test_update_record(self):
        service_names = ['name2._type2._tcp.local.', 'name._type._tcp.local.', 'name._type._udp.local']
        service_types = ['_type2._tcp.local.', '_type._tcp.local.', '_type._udp.local.']

        service_added_count = 0
        service_removed_count = 0
        service_add_event = Event()
        service_removed_event = Event()

        class MyServiceListener(r.ServiceListener):
            def add_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
                nonlocal service_added_count
                service_added_count += 1
                if service_added_count == 3:
                    service_add_event.set()

            def remove_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
                nonlocal service_removed_count
                service_removed_count += 1
                if service_removed_count == 3:
                    service_removed_event.set()

        def mock_incoming_msg(
            service_state_change: r.ServiceStateChange, service_type: str, service_name: str, ttl: int
        ) -> r.DNSIncoming:
            generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
            generated.add_answer_at_time(
                r.DNSPointer(service_type, const._TYPE_PTR, const._CLASS_IN, ttl, service_name), 0
            )
            return r.DNSIncoming(generated.packets()[0])

        zeroconf = r.Zeroconf(interfaces=['127.0.0.1'])
        service_browser = r.ServiceBrowser(zeroconf, service_types, listener=MyServiceListener())

        try:
            wait_time = 3

            # all three services added
            _inject_response(
                zeroconf,
                mock_incoming_msg(r.ServiceStateChange.Added, service_types[0], service_names[0], 120),
            )
            _inject_response(
                zeroconf,
                mock_incoming_msg(r.ServiceStateChange.Added, service_types[1], service_names[1], 120),
            )
            time.sleep(0.1)

            called_with_refresh_time_check = False

            def _mock_get_expiration_time(self, percent):
                nonlocal called_with_refresh_time_check
                if percent == const._EXPIRE_REFRESH_TIME_PERCENT:
                    called_with_refresh_time_check = True
                    return 0
                return self.created + (percent * self.ttl * 10)

            # Set an expire time that will force a refresh
            with patch("zeroconf.DNSRecord.get_expiration_time", new=_mock_get_expiration_time):
                _inject_response(
                    zeroconf,
                    mock_incoming_msg(r.ServiceStateChange.Added, service_types[0], service_names[0], 120),
                )
                # Add the last record after updating the first one
                # to ensure the service_add_event only gets set
                # after the update
                _inject_response(
                    zeroconf,
                    mock_incoming_msg(r.ServiceStateChange.Added, service_types[2], service_names[2], 120),
                )
                service_add_event.wait(wait_time)
            assert called_with_refresh_time_check is True
            assert service_added_count == 3
            assert service_removed_count == 0

            _inject_response(
                zeroconf,
                mock_incoming_msg(r.ServiceStateChange.Updated, service_types[0], service_names[0], 0),
            )

            # all three services removed
            _inject_response(
                zeroconf,
                mock_incoming_msg(r.ServiceStateChange.Removed, service_types[0], service_names[0], 0),
            )
            _inject_response(
                zeroconf,
                mock_incoming_msg(r.ServiceStateChange.Removed, service_types[1], service_names[1], 0),
            )
            _inject_response(
                zeroconf,
                mock_incoming_msg(r.ServiceStateChange.Removed, service_types[2], service_names[2], 0),
            )
            service_removed_event.wait(wait_time)
            assert service_added_count == 3
            assert service_removed_count == 3
        except TypeError:
            # Cannot be patched with cython as get_expiration_time is immutable
            pass

        finally:
            assert len(zeroconf.listeners) == 1
            service_browser.cancel()
            time.sleep(0.2)
            assert len(zeroconf.listeners) == 0
            zeroconf.remove_all_service_listeners()
            zeroconf.close()


def test_backoff():
    got_query = Event()

    type_ = "_http._tcp.local."
    zeroconf_browser = Zeroconf(interfaces=['127.0.0.1'])
    _wait_for_start(zeroconf_browser)
    zeroconf_browser.question_history = QuestionHistoryWithoutSuppression()

    # we are going to patch the zeroconf send to check query transmission
    old_send = zeroconf_browser.async_send

    time_offset = 0.0
    start_time = time.monotonic() * 1000
    initial_query_interval = _services_browser._BROWSER_TIME / 1000

    def current_time_millis():
        """Current system time in milliseconds"""
        return start_time + time_offset * 1000

    def send(out, addr=const._MDNS_ADDR, port=const._MDNS_PORT, v6_flow_scope=()):
        """Sends an outgoing packet."""
        got_query.set()
        old_send(out, addr=addr, port=port, v6_flow_scope=v6_flow_scope)

    # patch the zeroconf send
    # patch the zeroconf current_time_millis
    # patch the backoff limit to prevent test running forever
    with patch.object(zeroconf_browser, "async_send", send), patch.object(
        _services_browser, "current_time_millis", current_time_millis
    ), patch.object(_services_browser, "_BROWSER_BACKOFF_LIMIT", 10), patch.object(
        _services_browser, "_FIRST_QUERY_DELAY_RANDOM_INTERVAL", (0, 0)
    ):
        # dummy service callback
        def on_service_state_change(zeroconf, service_type, state_change, name):
            pass

        browser = ServiceBrowser(zeroconf_browser, type_, [on_service_state_change])

        try:
            # Test that queries are sent at increasing intervals
            sleep_count = 0
            next_query_interval = 0.0
            expected_query_time = 0.0
            while True:
                sleep_count += 1
                got_query.wait(0.1)
                if time_offset == expected_query_time:
                    assert got_query.is_set()
                    got_query.clear()
                    if next_query_interval == _services_browser._BROWSER_BACKOFF_LIMIT:
                        # Only need to test up to the point where we've seen a query
                        # after the backoff limit has been hit
                        break
                    elif next_query_interval == 0:
                        next_query_interval = initial_query_interval
                        expected_query_time = initial_query_interval
                    else:
                        next_query_interval = min(
                            2 * next_query_interval, _services_browser._BROWSER_BACKOFF_LIMIT
                        )
                        expected_query_time += next_query_interval
                else:
                    assert not got_query.is_set()
                time_offset += initial_query_interval
                assert zeroconf_browser.loop is not None
                zeroconf_browser.loop.call_soon_threadsafe(browser._async_send_ready_queries_schedule_next)

        finally:
            browser.cancel()
            zeroconf_browser.close()


def test_first_query_delay():
    """Verify the first query is delayed.

    https://datatracker.ietf.org/doc/html/rfc6762#section-5.2
    """
    type_ = "_http._tcp.local."
    zeroconf_browser = Zeroconf(interfaces=['127.0.0.1'])
    _wait_for_start(zeroconf_browser)

    # we are going to patch the zeroconf send to check query transmission
    old_send = zeroconf_browser.async_send

    first_query_time = None

    def send(out, addr=const._MDNS_ADDR, port=const._MDNS_PORT):
        """Sends an outgoing packet."""
        nonlocal first_query_time
        if first_query_time is None:
            first_query_time = current_time_millis()
        old_send(out, addr=addr, port=port)

    # patch the zeroconf send
    with patch.object(zeroconf_browser, "async_send", send):
        # dummy service callback
        def on_service_state_change(zeroconf, service_type, state_change, name):
            pass

        start_time = current_time_millis()
        browser = ServiceBrowser(zeroconf_browser, type_, [on_service_state_change])
        time.sleep(millis_to_seconds(_services_browser._FIRST_QUERY_DELAY_RANDOM_INTERVAL[1] + 5))
        try:
            assert (
                current_time_millis() - start_time > _services_browser._FIRST_QUERY_DELAY_RANDOM_INTERVAL[0]
            )
        finally:
            browser.cancel()
            zeroconf_browser.close()


def test_asking_default_is_asking_qm_questions_after_the_first_qu():
    """Verify the service browser's first question is QU and subsequent ones are QM questions."""
    type_ = "_quservice._tcp.local."
    zeroconf_browser = Zeroconf(interfaces=['127.0.0.1'])

    # we are going to patch the zeroconf send to check query transmission
    old_send = zeroconf_browser.async_send

    first_outgoing = None
    second_outgoing = None

    def send(out, addr=const._MDNS_ADDR, port=const._MDNS_PORT):
        """Sends an outgoing packet."""
        nonlocal first_outgoing
        nonlocal second_outgoing
        if first_outgoing is not None and second_outgoing is None:  # type: ignore[unreachable]
            second_outgoing = out  # type: ignore[unreachable]
        if first_outgoing is None:
            first_outgoing = out
        old_send(out, addr=addr, port=port)

    # patch the zeroconf send
    with patch.object(zeroconf_browser, "async_send", send):
        # dummy service callback
        def on_service_state_change(zeroconf, service_type, state_change, name):
            pass

        browser = ServiceBrowser(zeroconf_browser, type_, [on_service_state_change], delay=5)
        time.sleep(millis_to_seconds(_services_browser._FIRST_QUERY_DELAY_RANDOM_INTERVAL[1] + 120 + 50))
        try:
            assert first_outgoing.questions[0].unicast is True  # type: ignore[union-attr]
            assert second_outgoing.questions[0].unicast is False  # type: ignore[attr-defined]
        finally:
            browser.cancel()
            zeroconf_browser.close()


def test_asking_qm_questions():
    """Verify explictly asking QM questions."""
    type_ = "_quservice._tcp.local."
    zeroconf_browser = Zeroconf(interfaces=['127.0.0.1'])

    # we are going to patch the zeroconf send to check query transmission
    old_send = zeroconf_browser.async_send

    first_outgoing = None

    def send(out, addr=const._MDNS_ADDR, port=const._MDNS_PORT):
        """Sends an outgoing packet."""
        nonlocal first_outgoing
        if first_outgoing is None:
            first_outgoing = out
        old_send(out, addr=addr, port=port)

    # patch the zeroconf send
    with patch.object(zeroconf_browser, "async_send", send):
        # dummy service callback
        def on_service_state_change(zeroconf, service_type, state_change, name):
            pass

        browser = ServiceBrowser(
            zeroconf_browser, type_, [on_service_state_change], question_type=r.DNSQuestionType.QM
        )
        time.sleep(millis_to_seconds(_services_browser._FIRST_QUERY_DELAY_RANDOM_INTERVAL[1] + 5))
        try:
            assert first_outgoing.questions[0].unicast is False  # type: ignore[union-attr]
        finally:
            browser.cancel()
            zeroconf_browser.close()


def test_asking_qu_questions():
    """Verify the service browser can ask QU questions."""
    type_ = "_quservice._tcp.local."
    zeroconf_browser = Zeroconf(interfaces=['127.0.0.1'])

    # we are going to patch the zeroconf send to check query transmission
    old_send = zeroconf_browser.async_send

    first_outgoing = None

    def send(out, addr=const._MDNS_ADDR, port=const._MDNS_PORT):
        """Sends an outgoing packet."""
        nonlocal first_outgoing
        if first_outgoing is None:
            first_outgoing = out
        old_send(out, addr=addr, port=port)

    # patch the zeroconf send
    with patch.object(zeroconf_browser, "async_send", send):
        # dummy service callback
        def on_service_state_change(zeroconf, service_type, state_change, name):
            pass

        browser = ServiceBrowser(
            zeroconf_browser, type_, [on_service_state_change], question_type=r.DNSQuestionType.QU
        )
        time.sleep(millis_to_seconds(_services_browser._FIRST_QUERY_DELAY_RANDOM_INTERVAL[1] + 5))
        try:
            assert first_outgoing.questions[0].unicast is True  # type: ignore[union-attr]
        finally:
            browser.cancel()
            zeroconf_browser.close()


def test_legacy_record_update_listener():
    """Test a RecordUpdateListener that does not implement update_records."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])

    with pytest.raises(RuntimeError):
        r.RecordUpdateListener().update_record(
            zc, 0, r.DNSRecord('irrelevant', const._TYPE_SRV, const._CLASS_IN, const._DNS_HOST_TTL)
        )

    updates = []

    class LegacyRecordUpdateListener(r.RecordUpdateListener):
        """A RecordUpdateListener that does not implement update_records."""

        def update_record(self, zc: 'Zeroconf', now: float, record: r.DNSRecord) -> None:
            nonlocal updates
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
        f'{name}.{type_}',
        80,
        0,
        0,
        {'path': '/~paulsm/'},
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )

    zc.register_service(info_service)

    time.sleep(0.001)

    browser.cancel()

    assert len(updates)
    assert len([isinstance(update, r.DNSPointer) and update.name == type_ for update in updates]) >= 1

    zc.remove_listener(listener)
    # Removing a second time should not throw
    zc.remove_listener(listener)

    zc.close()


def test_service_browser_is_aware_of_port_changes():
    """Test that the ServiceBrowser is aware of port changes."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_hap._tcp.local."
    registration_name = "xxxyyy.%s" % type_

    callbacks = []

    # dummy service callback
    def on_service_state_change(zeroconf, service_type, state_change, name):
        """Dummy callback."""
        nonlocal callbacks
        if name == registration_name:
            callbacks.append((service_type, state_change, name))

    browser = ServiceBrowser(zc, type_, [on_service_state_change])

    desc = {'path': '/~paulsm/'}
    address_parsed = "10.0.1.2"
    address = socket.inet_aton(address_parsed)
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[address])

    def mock_incoming_msg(records: Iterable[r.DNSRecord]) -> r.DNSIncoming:
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        for record in records:
            generated.add_answer_at_time(record, 0)
        return r.DNSIncoming(generated.packets()[0])

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_pointer(), info.dns_service(), info.dns_text(), *info.dns_addresses()]),
    )
    time.sleep(0.1)

    assert callbacks == [('_hap._tcp.local.', ServiceStateChange.Added, 'xxxyyy._hap._tcp.local.')]
    service_info = zc.get_service_info(type_, registration_name)
    assert service_info is not None
    assert service_info.port == 80

    info.port = 400
    info._dns_service_cache = None  # we are mutating the record so clear the cache

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_service()]),
    )
    time.sleep(0.1)

    assert callbacks == [
        ('_hap._tcp.local.', ServiceStateChange.Added, 'xxxyyy._hap._tcp.local.'),
        ('_hap._tcp.local.', ServiceStateChange.Updated, 'xxxyyy._hap._tcp.local.'),
    ]
    service_info = zc.get_service_info(type_, registration_name)
    assert service_info is not None
    assert service_info.port == 400
    browser.cancel()

    zc.close()


def test_service_browser_listeners_update_service():
    """Test that the ServiceBrowser ServiceListener that implements update_service."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_hap._tcp.local."
    registration_name = "xxxyyy.%s" % type_
    callbacks = []

    class MyServiceListener(r.ServiceListener):
        def add_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("add", type_, name))

        def remove_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("remove", type_, name))

        def update_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("update", type_, name))

    listener = MyServiceListener()

    browser = r.ServiceBrowser(zc, type_, None, listener)

    desc = {'path': '/~paulsm/'}
    address_parsed = "10.0.1.2"
    address = socket.inet_aton(address_parsed)
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[address])

    def mock_incoming_msg(records: Iterable[r.DNSRecord]) -> r.DNSIncoming:
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        for record in records:
            generated.add_answer_at_time(record, 0)
        return r.DNSIncoming(generated.packets()[0])

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_pointer(), info.dns_service(), info.dns_text(), *info.dns_addresses()]),
    )
    time.sleep(0.2)
    info._dns_service_cache = None  # we are mutating the record so clear the cache

    info.port = 400
    _inject_response(
        zc,
        mock_incoming_msg([info.dns_service()]),
    )
    time.sleep(0.2)

    assert callbacks == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
    ]
    browser.cancel()

    zc.close()


def test_service_browser_listeners_no_update_service():
    """Test that the ServiceBrowser ServiceListener that does not implement update_service."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_hap._tcp.local."
    registration_name = "xxxyyy.%s" % type_
    callbacks = []

    class MyServiceListener(r.ServiceListener):
        def add_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("add", type_, name))

        def remove_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("remove", type_, name))

    listener = MyServiceListener()

    browser = r.ServiceBrowser(zc, type_, None, listener)

    desc = {'path': '/~paulsm/'}
    address_parsed = "10.0.1.2"
    address = socket.inet_aton(address_parsed)
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[address])

    def mock_incoming_msg(records: Iterable[r.DNSRecord]) -> r.DNSIncoming:
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        for record in records:
            generated.add_answer_at_time(record, 0)
        return r.DNSIncoming(generated.packets()[0])

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_pointer(), info.dns_service(), info.dns_text(), *info.dns_addresses()]),
    )
    time.sleep(0.2)
    info.port = 400
    info._dns_service_cache = None  # we are mutating the record so clear the cache

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_service()]),
    )
    time.sleep(0.2)

    assert callbacks == [
        ('add', type_, registration_name),
    ]
    browser.cancel()

    zc.close()


def test_servicebrowser_uses_non_strict_names():
    """Verify we can look for technically invalid names as we cannot change what others do."""

    # dummy service callback
    def on_service_state_change(zeroconf, service_type, state_change, name):
        pass

    zc = r.Zeroconf(interfaces=['127.0.0.1'])
    browser = ServiceBrowser(zc, ["_tivo-videostream._tcp.local."], [on_service_state_change])
    browser.cancel()

    # Still fail on completely invalid
    with pytest.raises(r.BadTypeInNameException):
        browser = ServiceBrowser(zc, ["tivo-videostream._tcp.local."], [on_service_state_change])
    zc.close()


def test_group_ptr_queries_with_known_answers():
    questions_with_known_answers: _services_browser._QuestionWithKnownAnswers = {}
    now = current_time_millis()
    for i in range(120):
        name = f"_hap{i}._tcp._local."
        questions_with_known_answers[DNSQuestion(name, const._TYPE_PTR, const._CLASS_IN)] = {
            DNSPointer(
                name,
                const._TYPE_PTR,
                const._CLASS_IN,
                4500,
                f"zoo{counter}.{name}",
            )
            for counter in range(i)
        }
    outs = _services_browser._group_ptr_queries_with_known_answers(now, True, questions_with_known_answers)
    for out in outs:
        packets = out.packets()
        # If we generate multiple packets there must
        # only be one question
        assert len(packets) == 1 or len(out.questions) == 1


# This test uses asyncio because it needs to access the cache directly
# which is not threadsafe
@pytest.mark.asyncio
async def test_generate_service_query_suppress_duplicate_questions():
    """Generate a service query for sending with zeroconf.send."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    now = current_time_millis()
    name = "_suppresstest._tcp.local."
    question = r.DNSQuestion(name, const._TYPE_PTR, const._CLASS_IN)
    answer = r.DNSPointer(
        name,
        const._TYPE_PTR,
        const._CLASS_IN,
        10000,
        f'known-to-other.{name}',
    )
    other_known_answers: Set[r.DNSRecord] = {answer}
    zc.question_history.add_question_at_time(question, now, other_known_answers)
    assert zc.question_history.suppresses(question, now, other_known_answers)

    # The known answer list is different, do not suppress
    outs = _services_browser.generate_service_query(zc, now, [name], multicast=True)
    assert outs

    zc.cache.async_add_records([answer])
    # The known answer list contains all the asked questions in the history
    # we should suppress

    outs = _services_browser.generate_service_query(zc, now, [name], multicast=True)
    assert not outs

    # We do not suppress once the question history expires
    outs = _services_browser.generate_service_query(zc, now + 1000, [name], multicast=True)
    assert outs

    # We do not suppress QU queries ever
    outs = _services_browser.generate_service_query(zc, now, [name], multicast=False)
    assert outs

    zc.question_history.async_expire(now + 2000)
    # No suppression after clearing the history
    outs = _services_browser.generate_service_query(zc, now, [name], multicast=True)
    assert outs

    # The previous query we just sent is still remembered and
    # the next one is suppressed
    outs = _services_browser.generate_service_query(zc, now, [name], multicast=True)
    assert not outs

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_query_scheduler():
    delay = const._BROWSER_TIME
    types_ = {"_hap._tcp.local.", "_http._tcp.local."}
    query_scheduler = _services_browser.QueryScheduler(types_, delay, (0, 0))

    now = current_time_millis()
    query_scheduler.start(now)

    # Test query interval is increasing
    assert query_scheduler.millis_to_wait(now - 1) == 1
    assert query_scheduler.millis_to_wait(now) == 0
    assert query_scheduler.millis_to_wait(now + 1) == 0

    assert set(query_scheduler.process_ready_types(now)) == types_
    assert set(query_scheduler.process_ready_types(now)) == set()
    assert query_scheduler.millis_to_wait(now) == pytest.approx(delay, 0.00001)

    assert set(query_scheduler.process_ready_types(now + delay)) == types_
    assert set(query_scheduler.process_ready_types(now + delay)) == set()
    assert query_scheduler.millis_to_wait(now) == pytest.approx(delay * 3, 0.00001)

    assert set(query_scheduler.process_ready_types(now + delay * 3)) == types_
    assert set(query_scheduler.process_ready_types(now + delay * 3)) == set()
    assert query_scheduler.millis_to_wait(now) == pytest.approx(delay * 7, 0.00001)

    assert set(query_scheduler.process_ready_types(now + delay * 7)) == types_
    assert set(query_scheduler.process_ready_types(now + delay * 7)) == set()
    assert query_scheduler.millis_to_wait(now) == pytest.approx(delay * 15, 0.00001)

    assert set(query_scheduler.process_ready_types(now + delay * 15)) == types_
    assert set(query_scheduler.process_ready_types(now + delay * 15)) == set()

    # Test if we reschedule 1 second later, the millis_to_wait goes up by 1
    query_scheduler.reschedule_type("_hap._tcp.local.", now + delay * 16)
    assert query_scheduler.millis_to_wait(now) == pytest.approx(delay * 16, 0.00001)

    assert set(query_scheduler.process_ready_types(now + delay * 15)) == set()

    # Test if we reschedule 1 second later... and its ready for processing
    assert set(query_scheduler.process_ready_types(now + delay * 16)) == {"_hap._tcp.local."}
    assert query_scheduler.millis_to_wait(now) == pytest.approx(delay * 31, 0.00001)
    assert set(query_scheduler.process_ready_types(now + delay * 20)) == set()

    assert set(query_scheduler.process_ready_types(now + delay * 31)) == {"_http._tcp.local."}


def test_service_browser_matching():
    """Test that the ServiceBrowser matching does not match partial names."""

    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_http._tcp.local."
    registration_name = "xxxyyy.%s" % type_
    not_match_type_ = "_asustor-looksgood_http._tcp.local."
    not_match_registration_name = "xxxyyy.%s" % not_match_type_
    callbacks = []

    class MyServiceListener(r.ServiceListener):
        def add_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("add", type_, name))

        def remove_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("remove", type_, name))

        def update_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("update", type_, name))

    listener = MyServiceListener()

    browser = r.ServiceBrowser(zc, type_, None, listener)

    desc = {'path': '/~paulsm/'}
    address_parsed = "10.0.1.2"
    address = socket.inet_aton(address_parsed)
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[address])
    should_not_match = ServiceInfo(
        not_match_type_, not_match_registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[address]
    )

    def mock_incoming_msg(records: Iterable[r.DNSRecord]) -> r.DNSIncoming:
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        for record in records:
            generated.add_answer_at_time(record, 0)
        return r.DNSIncoming(generated.packets()[0])

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_pointer(), info.dns_service(), info.dns_text(), *info.dns_addresses()]),
    )
    _inject_response(
        zc,
        mock_incoming_msg(
            [
                should_not_match.dns_pointer(),
                should_not_match.dns_service(),
                should_not_match.dns_text(),
                *should_not_match.dns_addresses(),
            ]
        ),
    )
    time.sleep(0.2)
    info.port = 400
    info._dns_service_cache = None  # we are mutating the record so clear the cache

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_service()]),
    )
    should_not_match.port = 400
    _inject_response(
        zc,
        mock_incoming_msg([should_not_match.dns_service()]),
    )
    time.sleep(0.2)

    assert callbacks == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
    ]
    browser.cancel()

    zc.close()


@patch.object(record_manager, '_DNS_PTR_MIN_TTL', 1)
@patch.object(_engine, "_CACHE_CLEANUP_INTERVAL", 0.01)
def test_service_browser_expire_callbacks():
    """Test that the ServiceBrowser matching does not match partial names."""
    # instantiate a zeroconf instance
    zc = Zeroconf(interfaces=['127.0.0.1'])
    # start a browser
    type_ = "_old._tcp.local."
    registration_name = "uniquezip323.%s" % type_
    callbacks = []

    class MyServiceListener(r.ServiceListener):
        def add_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("add", type_, name))

        def remove_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("remove", type_, name))

        def update_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            if name == registration_name:
                callbacks.append(("update", type_, name))

    listener = MyServiceListener()

    browser = r.ServiceBrowser(zc, type_, None, listener)

    desc = {'path': '/~paul2/'}
    address_parsed = "10.0.1.3"
    address = socket.inet_aton(address_parsed)
    info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "newname-2.local.",
        host_ttl=1,
        other_ttl=1,
        addresses=[address],
    )

    def mock_incoming_msg(records: Iterable[r.DNSRecord]) -> r.DNSIncoming:
        generated = r.DNSOutgoing(const._FLAGS_QR_RESPONSE)
        for record in records:
            generated.add_answer_at_time(record, 0)
        return r.DNSIncoming(generated.packets()[0])

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_pointer(), info.dns_service(), info.dns_text(), *info.dns_addresses()]),
    )
    time.sleep(0.3)
    info.port = 400
    info._dns_service_cache = None  # we are mutating the record so clear the cache

    _inject_response(
        zc,
        mock_incoming_msg([info.dns_service()]),
    )

    for _ in range(10):
        time.sleep(0.05)
        if len(callbacks) == 2:
            break

    assert callbacks == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
    ]

    for _ in range(25):
        time.sleep(0.05)
        if len(callbacks) == 3:
            break

    assert callbacks == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
        ('remove', type_, registration_name),
    ]
    browser.cancel()

    zc.close()
