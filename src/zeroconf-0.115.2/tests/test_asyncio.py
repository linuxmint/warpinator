#!/usr/bin/env python


"""Unit tests for aio.py."""

import asyncio
import logging
import os
import socket
import threading
import time
from typing import cast
from unittest.mock import ANY, call, patch

import pytest

import zeroconf._services.browser as _services_browser
from zeroconf import (
    DNSAddress,
    DNSIncoming,
    DNSOutgoing,
    DNSPointer,
    DNSQuestion,
    DNSService,
    DNSText,
    NotRunningException,
    ServiceStateChange,
    Zeroconf,
    const,
)
from zeroconf._exceptions import (
    BadTypeInNameException,
    NonUniqueNameException,
    ServiceNameAlreadyRegistered,
)
from zeroconf._services import ServiceListener
from zeroconf._services.info import ServiceInfo
from zeroconf._utils.time import current_time_millis
from zeroconf.asyncio import (
    AsyncServiceBrowser,
    AsyncServiceInfo,
    AsyncZeroconf,
    AsyncZeroconfServiceTypes,
)
from zeroconf.const import _LISTENER_TIME

from . import QuestionHistoryWithoutSuppression, _clear_cache, has_working_ipv6

log = logging.getLogger('zeroconf')
original_logging_level = logging.NOTSET


def setup_module():
    global original_logging_level
    original_logging_level = log.level
    log.setLevel(logging.DEBUG)


def teardown_module():
    if original_logging_level != logging.NOTSET:
        log.setLevel(original_logging_level)


@pytest.fixture(autouse=True)
def verify_threads_ended():
    """Verify that the threads are not running after the test."""
    threads_before = frozenset(threading.enumerate())
    yield
    threads_after = frozenset(threading.enumerate())
    non_executor_threads = frozenset(
        thread
        for thread in threads_after
        if "asyncio" not in thread.name and "ThreadPoolExecutor" not in thread.name
    )
    threads = non_executor_threads - threads_before
    assert not threads


@pytest.mark.asyncio
async def test_async_basic_usage() -> None:
    """Test we can create and close the instance."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_close_twice() -> None:
    """Test we can close twice."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.async_close()
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_with_sync_passed_in() -> None:
    """Test we can create and close the instance when passing in a sync Zeroconf."""
    zc = Zeroconf(interfaces=['127.0.0.1'])
    aiozc = AsyncZeroconf(zc=zc)
    assert aiozc.zeroconf is zc
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_with_sync_passed_in_closed_in_async() -> None:
    """Test caller closes the sync version in async."""
    zc = Zeroconf(interfaces=['127.0.0.1'])
    aiozc = AsyncZeroconf(zc=zc)
    assert aiozc.zeroconf is zc
    zc.close()
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_sync_within_event_loop_executor() -> None:
    """Test sync version still works from an executor within an event loop."""

    def sync_code():
        zc = Zeroconf(interfaces=['127.0.0.1'])
        assert zc.get_service_info("_neverused._tcp.local.", "xneverused._neverused._tcp.local.", 10) is None
        zc.close()

    await asyncio.get_event_loop().run_in_executor(None, sync_code)


@pytest.mark.asyncio
async def test_async_service_registration() -> None:
    """Test registering services broadcasts the registration by default."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test1-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    calls = []

    class MyListener(ServiceListener):
        def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("add", type, name))

        def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("remove", type, name))

        def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("update", type, name))

    listener = MyListener()

    aiozc.zeroconf.add_service_listener(type_, listener)

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
    task = await aiozc.async_register_service(info)
    await task
    new_info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.3")],
    )
    task = await aiozc.async_update_service(new_info)
    await task
    assert new_info.dns_service().server_key == "ash-2.local."
    new_info.server = "ash-3.local."
    task = await aiozc.async_update_service(new_info)
    await task
    assert new_info.dns_service().server_key == "ash-3.local."

    task = await aiozc.async_unregister_service(new_info)
    await task
    await aiozc.async_close()

    assert calls == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
        ('update', type_, registration_name),
        ('remove', type_, registration_name),
    ]


@pytest.mark.asyncio
async def test_async_service_registration_with_server_missing() -> None:
    """Test registering a service with the server not specified.

    For backwards compatibility, the server should be set to the
    name that was passed in.
    """
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test1-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    calls = []

    class MyListener(ServiceListener):
        def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("add", type, name))

        def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("remove", type, name))

        def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("update", type, name))

    listener = MyListener()

    aiozc.zeroconf.add_service_listener(type_, listener)

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        addresses=[socket.inet_aton("10.0.1.2")],
    )
    task = await aiozc.async_register_service(info)
    await task

    assert info.server == registration_name
    assert info.server_key == registration_name
    new_info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.3")],
    )
    task = await aiozc.async_update_service(new_info)
    await task

    task = await aiozc.async_unregister_service(new_info)
    await task
    await aiozc.async_close()

    assert calls == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
        ('remove', type_, registration_name),
    ]


@pytest.mark.asyncio
async def test_async_service_registration_same_server_different_ports() -> None:
    """Test registering services with the same server with different srv records."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test1-srvc-type._tcp.local."
    name = "xxxyyy"
    name2 = "xxxyyy2"

    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name2}.{type_}"

    calls = []

    class MyListener(ServiceListener):
        def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("add", type, name))

        def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("remove", type, name))

        def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("update", type, name))

    listener = MyListener()

    aiozc.zeroconf.add_service_listener(type_, listener)

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
    info2 = ServiceInfo(
        type_,
        registration_name2,
        81,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )
    tasks = []
    tasks.append(await aiozc.async_register_service(info))
    tasks.append(await aiozc.async_register_service(info2))
    await asyncio.gather(*tasks)

    task = await aiozc.async_unregister_service(info)
    await task
    entries = aiozc.zeroconf.cache.async_entries_with_server("ash-2.local.")
    assert len(entries) == 1
    assert info2.dns_service() in entries
    await aiozc.async_close()
    assert calls == [
        ('add', type_, registration_name),
        ('add', type_, registration_name2),
        ('remove', type_, registration_name),
        ('remove', type_, registration_name2),
    ]


@pytest.mark.asyncio
async def test_async_service_registration_same_server_same_ports() -> None:
    """Test registering services with the same server with the exact same srv record."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test1-srvc-type._tcp.local."
    name = "xxxyyy"
    name2 = "xxxyyy2"

    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name2}.{type_}"

    calls = []

    class MyListener(ServiceListener):
        def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("add", type, name))

        def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("remove", type, name))

        def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("update", type, name))

    listener = MyListener()

    aiozc.zeroconf.add_service_listener(type_, listener)

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
    info2 = ServiceInfo(
        type_,
        registration_name2,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )
    tasks = []
    tasks.append(await aiozc.async_register_service(info))
    tasks.append(await aiozc.async_register_service(info2))
    await asyncio.gather(*tasks)

    task = await aiozc.async_unregister_service(info)
    await task
    entries = aiozc.zeroconf.cache.async_entries_with_server("ash-2.local.")
    assert len(entries) == 1
    assert info2.dns_service() in entries
    await aiozc.async_close()
    assert calls == [
        ('add', type_, registration_name),
        ('add', type_, registration_name2),
        ('remove', type_, registration_name),
        ('remove', type_, registration_name2),
    ]


@pytest.mark.asyncio
async def test_async_service_registration_name_conflict() -> None:
    """Test registering services throws on name conflict."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test-srvc2-type._tcp.local."
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
    task = await aiozc.async_register_service(info)
    await task

    with pytest.raises(NonUniqueNameException):
        task = await aiozc.async_register_service(info)
        await task

    with pytest.raises(ServiceNameAlreadyRegistered):
        task = await aiozc.async_register_service(info, cooperating_responders=True)
        await task

    conflicting_info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-3.local.",
        addresses=[socket.inet_aton("10.0.1.3")],
    )

    with pytest.raises(NonUniqueNameException):
        task = await aiozc.async_register_service(conflicting_info)
        await task

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_service_registration_name_does_not_match_type() -> None:
    """Test registering services throws when the name does not match the type."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test-srvc3-type._tcp.local."
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
    info.type = "_wrong._tcp.local."
    with pytest.raises(BadTypeInNameException):
        task = await aiozc.async_register_service(info)
        await task
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_service_registration_name_strict_check() -> None:
    """Test registering services throws when the name does not comply."""
    zc = Zeroconf(interfaces=['127.0.0.1'])
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_ibisip_http._tcp.local."
    name = "CustomerInformationService-F4D4895E9EEB"
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
    with pytest.raises(BadTypeInNameException):
        await zc.async_check_service(info, allow_name_change=False)

    with pytest.raises(BadTypeInNameException):
        task = await aiozc.async_register_service(info)
        await task

    await zc.async_check_service(info, allow_name_change=False, strict=False)
    task = await aiozc.async_register_service(info, strict=False)
    await task

    await aiozc.async_unregister_service(info)
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_tasks() -> None:
    """Test awaiting broadcast tasks"""

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test-srvc4-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    calls = []

    class MyListener(ServiceListener):
        def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("add", type, name))

        def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("remove", type, name))

        def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
            calls.append(("update", type, name))

    listener = MyListener()
    aiozc.zeroconf.add_service_listener(type_, listener)

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
    task = await aiozc.async_register_service(info)
    assert isinstance(task, asyncio.Task)
    await task

    new_info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.3")],
    )
    task = await aiozc.async_update_service(new_info)
    assert isinstance(task, asyncio.Task)
    await task

    task = await aiozc.async_unregister_service(new_info)
    assert isinstance(task, asyncio.Task)
    await task

    await aiozc.async_close()

    assert calls == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
        ('remove', type_, registration_name),
    ]


@pytest.mark.asyncio
async def test_async_wait_unblocks_on_update() -> None:
    """Test async_wait will unblock on update."""

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test-srvc4-type._tcp.local."
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
    task = await aiozc.async_register_service(info)

    # Should unblock due to update from the
    # registration
    now = current_time_millis()
    await aiozc.zeroconf.async_wait(50000)
    assert current_time_millis() - now < 3000
    await task

    now = current_time_millis()
    await aiozc.zeroconf.async_wait(50)
    assert current_time_millis() - now < 1000

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_service_info_async_request() -> None:
    """Test registering services broadcasts and query with AsyncServceInfo.async_request."""
    if not has_working_ipv6() or os.environ.get('SKIP_IPV6'):
        pytest.skip('Requires IPv6')

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test1-srvc-type._tcp.local."
    name = "xxxyyy"
    name2 = "abc"
    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name2}.{type_}"

    # Start a tasks BEFORE the registration that will keep trying
    # and see the registration a bit later
    get_service_info_task1 = asyncio.ensure_future(aiozc.async_get_service_info(type_, registration_name))
    await asyncio.sleep(_LISTENER_TIME / 1000 / 2)
    get_service_info_task2 = asyncio.ensure_future(aiozc.async_get_service_info(type_, registration_name))

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-1.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )
    info2 = ServiceInfo(
        type_,
        registration_name2,
        80,
        0,
        0,
        desc,
        "ash-5.local.",
        addresses=[socket.inet_aton("10.0.1.5")],
    )
    tasks = []
    tasks.append(await aiozc.async_register_service(info))
    tasks.append(await aiozc.async_register_service(info2))
    await asyncio.gather(*tasks)

    aiosinfo = await get_service_info_task1
    assert aiosinfo is not None
    assert aiosinfo.addresses == [socket.inet_aton("10.0.1.2")]

    aiosinfo = await get_service_info_task2
    assert aiosinfo is not None
    assert aiosinfo.addresses == [socket.inet_aton("10.0.1.2")]

    aiosinfo = await aiozc.async_get_service_info(type_, registration_name)
    assert aiosinfo is not None
    assert aiosinfo.addresses == [socket.inet_aton("10.0.1.2")]

    new_info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.3"), socket.inet_pton(socket.AF_INET6, "6001:db8::1")],
    )

    task = await aiozc.async_update_service(new_info)
    await task

    aiosinfo = await aiozc.async_get_service_info(type_, registration_name)
    assert aiosinfo is not None
    assert aiosinfo.addresses == [socket.inet_aton("10.0.1.3")]

    aiosinfos = await asyncio.gather(
        aiozc.async_get_service_info(type_, registration_name),
        aiozc.async_get_service_info(type_, registration_name2),
    )
    assert aiosinfos[0] is not None
    assert aiosinfos[0].addresses == [socket.inet_aton("10.0.1.3")]
    assert aiosinfos[1] is not None
    assert aiosinfos[1].addresses == [socket.inet_aton("10.0.1.5")]

    aiosinfo = AsyncServiceInfo(type_, registration_name)
    _clear_cache(aiozc.zeroconf)
    # Generating the race condition is almost impossible
    # without patching since its a TOCTOU race
    with patch("zeroconf.asyncio.AsyncServiceInfo._is_complete", False):
        await aiosinfo.async_request(aiozc.zeroconf, 3000)
    assert aiosinfo is not None
    assert aiosinfo.addresses == [socket.inet_aton("10.0.1.3")]

    task = await aiozc.async_unregister_service(new_info)
    await task

    aiosinfo = await aiozc.async_get_service_info(type_, registration_name)
    assert aiosinfo is None

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_service_browser() -> None:
    """Test AsyncServiceBrowser."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test9-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    calls = []

    class MyListener(ServiceListener):
        def add_service(self, aiozc: Zeroconf, type: str, name: str) -> None:
            calls.append(("add", type, name))

        def remove_service(self, aiozc: Zeroconf, type: str, name: str) -> None:
            calls.append(("remove", type, name))

        def update_service(self, aiozc: Zeroconf, type: str, name: str) -> None:
            calls.append(("update", type, name))

    listener = MyListener()
    await aiozc.async_add_service_listener(type_, listener)

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
    task = await aiozc.async_register_service(info)
    await task
    new_info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-2.local.",
        addresses=[socket.inet_aton("10.0.1.3")],
    )
    task = await aiozc.async_update_service(new_info)
    await task
    task = await aiozc.async_unregister_service(new_info)
    await task
    await aiozc.zeroconf.async_wait(1)
    await aiozc.async_close()

    assert calls == [
        ('add', type_, registration_name),
        ('update', type_, registration_name),
        ('remove', type_, registration_name),
    ]


@pytest.mark.asyncio
async def test_async_context_manager() -> None:
    """Test using an async context manager."""
    type_ = "_test10-sr-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    async with AsyncZeroconf(interfaces=['127.0.0.1']) as aiozc:
        info = ServiceInfo(
            type_,
            registration_name,
            80,
            0,
            0,
            {'path': '/~paulsm/'},
            "ash-2.local.",
            addresses=[socket.inet_aton("10.0.1.2")],
        )
        task = await aiozc.async_register_service(info)
        await task
        aiosinfo = await aiozc.async_get_service_info(type_, registration_name)
        assert aiosinfo is not None


@pytest.mark.asyncio
async def test_service_browser_cancel_async_context_manager():
    """Test we can cancel an AsyncServiceBrowser with it being used as an async context manager."""

    # instantiate a zeroconf instance
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    type_ = "_hap._tcp.local."

    class MyServiceListener(ServiceListener):
        pass

    listener = MyServiceListener()

    browser = AsyncServiceBrowser(zc, type_, None, listener)

    assert cast(bool, browser.done) is False

    async with browser:
        pass

    assert cast(bool, browser.done) is True

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_unregister_all_services() -> None:
    """Test unregistering all services."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    type_ = "_test1-srvc-type._tcp.local."
    name = "xxxyyy"
    name2 = "abc"
    registration_name = f"{name}.{type_}"
    registration_name2 = f"{name2}.{type_}"

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_,
        registration_name,
        80,
        0,
        0,
        desc,
        "ash-1.local.",
        addresses=[socket.inet_aton("10.0.1.2")],
    )
    info2 = ServiceInfo(
        type_,
        registration_name2,
        80,
        0,
        0,
        desc,
        "ash-5.local.",
        addresses=[socket.inet_aton("10.0.1.5")],
    )
    tasks = []
    tasks.append(await aiozc.async_register_service(info))
    tasks.append(await aiozc.async_register_service(info2))
    await asyncio.gather(*tasks)

    tasks = []
    tasks.append(aiozc.async_get_service_info(type_, registration_name))
    tasks.append(aiozc.async_get_service_info(type_, registration_name2))
    results = await asyncio.gather(*tasks)
    assert results[0] is not None
    assert results[1] is not None

    await aiozc.async_unregister_all_services()
    _clear_cache(aiozc.zeroconf)

    tasks = []
    tasks.append(aiozc.async_get_service_info(type_, registration_name))
    tasks.append(aiozc.async_get_service_info(type_, registration_name2))
    results = await asyncio.gather(*tasks)
    assert results[0] is None
    assert results[1] is None

    # Verify we can call again
    await aiozc.async_unregister_all_services()

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_zeroconf_service_types():
    type_ = "_test-srvc-type._tcp.local."
    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    zeroconf_registrar = AsyncZeroconf(interfaces=['127.0.0.1'])
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
    task = await zeroconf_registrar.async_register_service(info)
    await task
    # Ensure we do not clear the cache until after the last broadcast is processed
    await asyncio.sleep(0.2)
    _clear_cache(zeroconf_registrar.zeroconf)
    try:
        service_types = await AsyncZeroconfServiceTypes.async_find(interfaces=['127.0.0.1'], timeout=2)
        assert type_ in service_types
        _clear_cache(zeroconf_registrar.zeroconf)
        service_types = await AsyncZeroconfServiceTypes.async_find(aiozc=zeroconf_registrar, timeout=2)
        assert type_ in service_types

    finally:
        await zeroconf_registrar.async_close()


@pytest.mark.asyncio
async def test_guard_against_running_serviceinfo_request_event_loop() -> None:
    """Test that running ServiceInfo.request from the event loop throws."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])

    service_info = AsyncServiceInfo("_hap._tcp.local.", "doesnotmatter._hap._tcp.local.")
    with pytest.raises(RuntimeError):
        service_info.request(aiozc.zeroconf, 3000)
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_service_browser_instantiation_generates_add_events_from_cache():
    """Test that the ServiceBrowser will generate Add events with the existing cache when starting."""

    # instantiate a zeroconf instance
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    type_ = "_hap._tcp.local."
    registration_name = "xxxyyy.%s" % type_
    callbacks = []

    class MyServiceListener(ServiceListener):
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

    desc = {'path': '/~paulsm/'}
    address_parsed = "10.0.1.2"
    address = socket.inet_aton(address_parsed)
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[address])
    zc.cache.async_add_records(
        [info.dns_pointer(), info.dns_service(), *info.dns_addresses(), info.dns_text()]
    )

    browser = AsyncServiceBrowser(zc, type_, None, listener)

    await asyncio.sleep(0)

    assert callbacks == [
        ('add', type_, registration_name),
    ]
    await browser.async_cancel()

    await aiozc.async_close()


@pytest.mark.asyncio
async def test_integration():
    service_added = asyncio.Event()
    service_removed = asyncio.Event()
    unexpected_ttl = asyncio.Event()
    got_query = asyncio.Event()

    type_ = "_http._tcp.local."
    registration_name = "xxxyyy.%s" % type_

    def on_service_state_change(zeroconf, service_type, state_change, name):
        if name == registration_name:
            if state_change is ServiceStateChange.Added:
                service_added.set()
            elif state_change is ServiceStateChange.Removed:
                service_removed.set()

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zeroconf_browser = aiozc.zeroconf
    zeroconf_browser.question_history = QuestionHistoryWithoutSuppression()
    await zeroconf_browser.async_wait_for_start()

    # we are going to patch the zeroconf send to check packet sizes
    old_send = zeroconf_browser.async_send

    time_offset = 0.0

    def _new_current_time_millis():
        """Current system time in milliseconds"""
        return (time.monotonic() * 1000) + (time_offset * 1000)

    expected_ttl = const._DNS_HOST_TTL
    nbr_answers = 0

    def send(out, addr=const._MDNS_ADDR, port=const._MDNS_PORT, v6_flow_scope=()):
        """Sends an outgoing packet."""
        pout = DNSIncoming(out.packets()[0])
        nonlocal nbr_answers
        for answer in pout.answers():
            nbr_answers += 1
            if not answer.ttl > expected_ttl / 2:
                unexpected_ttl.set()

        got_query.set()

        old_send(out, addr=addr, port=port, v6_flow_scope=v6_flow_scope)

    assert len(zeroconf_browser.engine.protocols) == 2

    aio_zeroconf_registrar = AsyncZeroconf(interfaces=['127.0.0.1'])
    zeroconf_registrar = aio_zeroconf_registrar.zeroconf
    await aio_zeroconf_registrar.zeroconf.async_wait_for_start()

    assert len(zeroconf_registrar.engine.protocols) == 2
    # patch the zeroconf send
    # patch the zeroconf current_time_millis
    # patch the backoff limit to ensure we always get one query every 1/4 of the DNS TTL
    # Disable duplicate question suppression and duplicate packet suppression for this test as it works
    # by asking the same question over and over
    with patch.object(zeroconf_browser, "async_send", send), patch(
        "zeroconf._services.browser.current_time_millis", _new_current_time_millis
    ), patch.object(_services_browser, "_BROWSER_BACKOFF_LIMIT", int(expected_ttl / 4)):
        service_added = asyncio.Event()
        service_removed = asyncio.Event()

        browser = AsyncServiceBrowser(zeroconf_browser, type_, [on_service_state_change])

        desc = {'path': '/~paulsm/'}
        info = ServiceInfo(
            type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
        )
        task = await aio_zeroconf_registrar.async_register_service(info)
        await task

        try:
            await asyncio.wait_for(service_added.wait(), 1)
            assert service_added.is_set()

            # Test that we receive queries containing answers only if the remaining TTL
            # is greater than half the original TTL
            sleep_count = 0
            test_iterations = 50

            while nbr_answers < test_iterations:
                # Increase simulated time shift by 1/4 of the TTL in seconds
                time_offset += expected_ttl / 4
                now = _new_current_time_millis()
                # Force the next query to be sent since we are testing
                # to see if the query contains answers and not the scheduler
                browser.query_scheduler._next_time[type_] = now + (1000 * expected_ttl)
                browser.reschedule_type(type_, now, now)
                sleep_count += 1
                await asyncio.wait_for(got_query.wait(), 1)
                got_query.clear()
                # Prevent the test running indefinitely in an error condition
                assert sleep_count < test_iterations * 4
            assert not unexpected_ttl.is_set()
            # Don't remove service, allow close() to cleanup
        finally:
            await aio_zeroconf_registrar.async_close()
            await asyncio.wait_for(service_removed.wait(), 1)
            assert service_removed.is_set()
            await browser.async_cancel()
            await aiozc.async_close()


@pytest.mark.asyncio
async def test_info_asking_default_is_asking_qm_questions_after_the_first_qu():
    """Verify the service info first question is QU and subsequent ones are QM questions."""
    type_ = "_quservice._tcp.local."
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zeroconf_info = aiozc.zeroconf

    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )

    zeroconf_info.registry.async_add(info)

    # we are going to patch the zeroconf send to check query transmission
    old_send = zeroconf_info.async_send

    first_outgoing = None
    second_outgoing = None

    def send(out, addr=const._MDNS_ADDR, port=const._MDNS_PORT):
        """Sends an outgoing packet."""
        nonlocal first_outgoing
        nonlocal second_outgoing
        if out.questions:
            if first_outgoing is not None and second_outgoing is None:  # type: ignore[unreachable]
                second_outgoing = out  # type: ignore[unreachable]
            if first_outgoing is None:
                first_outgoing = out
        old_send(out, addr=addr, port=port)

    # patch the zeroconf send
    with patch.object(zeroconf_info, "async_send", send):
        aiosinfo = AsyncServiceInfo(type_, registration_name)
        # Patch _is_complete so we send multiple times
        with patch("zeroconf.asyncio.AsyncServiceInfo._is_complete", False):
            await aiosinfo.async_request(aiozc.zeroconf, 1200)
        try:
            assert first_outgoing.questions[0].unicast is True  # type: ignore[union-attr]
            assert second_outgoing.questions[0].unicast is False  # type: ignore[attr-defined]
        finally:
            await aiozc.async_close()


@pytest.mark.asyncio
async def test_service_browser_ignores_unrelated_updates():
    """Test that the ServiceBrowser ignores unrelated updates."""

    # instantiate a zeroconf instance
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zc = aiozc.zeroconf
    type_ = "_veryuniqueone._tcp.local."
    registration_name = "xxxyyy.%s" % type_
    callbacks = []

    class MyServiceListener(ServiceListener):
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

    desc = {'path': '/~paulsm/'}
    address_parsed = "10.0.1.2"
    address = socket.inet_aton(address_parsed)
    info = ServiceInfo(type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[address])
    zc.cache.async_add_records(
        [
            info.dns_pointer(),
            info.dns_service(),
            *info.dns_addresses(),
            info.dns_text(),
            DNSService(
                "zoom._unrelated._tcp.local.",
                const._TYPE_SRV,
                const._CLASS_IN,
                const._DNS_HOST_TTL,
                0,
                0,
                81,
                'unrelated.local.',
            ),
        ]
    )

    browser = AsyncServiceBrowser(zc, type_, None, listener)

    generated = DNSOutgoing(const._FLAGS_QR_RESPONSE)
    generated.add_answer_at_time(
        DNSPointer(
            "_unrelated._tcp.local.",
            const._TYPE_PTR,
            const._CLASS_IN,
            const._DNS_OTHER_TTL,
            "zoom._unrelated._tcp.local.",
        ),
        0,
    )
    generated.add_answer_at_time(
        DNSAddress("unrelated.local.", const._TYPE_A, const._CLASS_IN, const._DNS_HOST_TTL, b"1234"),
        0,
    )
    generated.add_answer_at_time(
        DNSText(
            "zoom._unrelated._tcp.local.",
            const._TYPE_TXT,
            const._CLASS_IN | const._CLASS_UNIQUE,
            const._DNS_OTHER_TTL,
            b"zoom",
        ),
        0,
    )

    zc.record_manager.async_updates_from_response(DNSIncoming(generated.packets()[0]))
    zc.handle_response(DNSIncoming(generated.packets()[0]))

    await browser.async_cancel()
    await asyncio.sleep(0)

    assert callbacks == [
        ('add', type_, registration_name),
    ]
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_async_request_timeout():
    """Test that the timeout does not throw an exception and finishes close to the actual timeout."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.zeroconf.async_wait_for_start()
    start_time = current_time_millis()
    assert await aiozc.async_get_service_info("_notfound.local.", "notthere._notfound.local.") is None
    end_time = current_time_millis()
    await aiozc.async_close()
    # 3000ms for the default timeout
    # 1000ms for loaded systems + schedule overhead
    assert (end_time - start_time) < 3000 + 1000


@pytest.mark.asyncio
async def test_async_request_non_running_instance():
    """Test that the async_request throws when zeroconf is not running."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.async_close()
    with pytest.raises(NotRunningException):
        await aiozc.async_get_service_info("_notfound.local.", "notthere._notfound.local.")


@pytest.mark.asyncio
async def test_legacy_unicast_response(run_isolated):
    """Verify legacy unicast responses include questions and correct id."""
    type_ = "_mservice._tcp.local."
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.zeroconf.async_wait_for_start()

    name = "xxxyyy"
    registration_name = f"{name}.{type_}"

    desc = {'path': '/~paulsm/'}
    info = ServiceInfo(
        type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
    )

    aiozc.zeroconf.registry.async_add(info)
    query = DNSOutgoing(const._FLAGS_QR_QUERY, multicast=False, id_=888)
    question = DNSQuestion(info.type, const._TYPE_PTR, const._CLASS_IN)
    query.add_question(question)
    protocol = aiozc.zeroconf.engine.protocols[0]

    with patch.object(aiozc.zeroconf, "async_send") as send_mock:
        protocol.datagram_received(query.packets()[0], ('127.0.0.1', 6503))

    calls = send_mock.mock_calls
    # Verify the response is sent back on the socket it was recieved from
    assert calls == [call(ANY, '127.0.0.1', 6503, (), protocol.transport)]
    outgoing = send_mock.call_args[0][0]
    assert isinstance(outgoing, DNSOutgoing)
    assert outgoing.questions == [question]
    assert outgoing.id == query.id
    await aiozc.async_close()


@pytest.mark.asyncio
async def test_update_with_uppercase_names(run_isolated):
    """Test an ip update from a shelly which uses uppercase names."""
    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    await aiozc.zeroconf.async_wait_for_start()

    callbacks = []

    class MyServiceListener(ServiceListener):
        def add_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            callbacks.append(("add", type_, name))

        def remove_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            callbacks.append(("remove", type_, name))

        def update_service(self, zc, type_, name) -> None:  # type: ignore[no-untyped-def]
            nonlocal callbacks
            callbacks.append(("update", type_, name))

    listener = MyServiceListener()
    browser = AsyncServiceBrowser(aiozc.zeroconf, "_http._tcp.local.", None, listener)
    protocol = aiozc.zeroconf.engine.protocols[0]

    packet = b'\x00\x00\x84\x80\x00\x00\x00\n\x00\x00\x00\x00\t_services\x07_dns-sd\x04_udp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00\x14\x07_shelly\x04_tcp\x05local\x00\t_services\x07_dns-sd\x04_udp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00\x12\x05_http\x04_tcp\x05local\x00\x07_shelly\x04_tcp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00.\x19shellypro4pm-94b97ec07650\x07_shelly\x04_tcp\x05local\x00\x19shellypro4pm-94b97ec07650\x07_shelly\x04_tcp\x05local\x00\x00!\x80\x01\x00\x00\x00x\x00\'\x00\x00\x00\x00\x00P\x19ShellyPro4PM-94B97EC07650\x05local\x00\x19shellypro4pm-94b97ec07650\x07_shelly\x04_tcp\x05local\x00\x00\x10\x80\x01\x00\x00\x00x\x00"\napp=Pro4PM\x10ver=0.10.0-beta5\x05gen=2\x05_http\x04_tcp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00,\x19ShellyPro4PM-94B97EC07650\x05_http\x04_tcp\x05local\x00\x19ShellyPro4PM-94B97EC07650\x05_http\x04_tcp\x05local\x00\x00!\x80\x01\x00\x00\x00x\x00\'\x00\x00\x00\x00\x00P\x19ShellyPro4PM-94B97EC07650\x05local\x00\x19ShellyPro4PM-94B97EC07650\x05_http\x04_tcp\x05local\x00\x00\x10\x80\x01\x00\x00\x00x\x00\x06\x05gen=2\x19ShellyPro4PM-94B97EC07650\x05local\x00\x00\x01\x80\x01\x00\x00\x00x\x00\x04\xc0\xa8\xbc=\x19ShellyPro4PM-94B97EC07650\x05local\x00\x00/\x80\x01\x00\x00\x00x\x00$\x19ShellyPro4PM-94B97EC07650\x05local\x00\x00\x01@'  # noqa: E501
    protocol.datagram_received(packet, ('127.0.0.1', 6503))
    await asyncio.sleep(0)
    packet = b'\x00\x00\x84\x80\x00\x00\x00\n\x00\x00\x00\x00\t_services\x07_dns-sd\x04_udp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00\x14\x07_shelly\x04_tcp\x05local\x00\t_services\x07_dns-sd\x04_udp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00\x12\x05_http\x04_tcp\x05local\x00\x07_shelly\x04_tcp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00.\x19shellypro4pm-94b97ec07650\x07_shelly\x04_tcp\x05local\x00\x19shellypro4pm-94b97ec07650\x07_shelly\x04_tcp\x05local\x00\x00!\x80\x01\x00\x00\x00x\x00\'\x00\x00\x00\x00\x00P\x19ShellyPro4PM-94B97EC07650\x05local\x00\x19shellypro4pm-94b97ec07650\x07_shelly\x04_tcp\x05local\x00\x00\x10\x80\x01\x00\x00\x00x\x00"\napp=Pro4PM\x10ver=0.10.0-beta5\x05gen=2\x05_http\x04_tcp\x05local\x00\x00\x0c\x00\x01\x00\x00\x11\x94\x00,\x19ShellyPro4PM-94B97EC07650\x05_http\x04_tcp\x05local\x00\x19ShellyPro4PM-94B97EC07650\x05_http\x04_tcp\x05local\x00\x00!\x80\x01\x00\x00\x00x\x00\'\x00\x00\x00\x00\x00P\x19ShellyPro4PM-94B97EC07650\x05local\x00\x19ShellyPro4PM-94B97EC07650\x05_http\x04_tcp\x05local\x00\x00\x10\x80\x01\x00\x00\x00x\x00\x06\x05gen=2\x19ShellyPro4PM-94B97EC07650\x05local\x00\x00\x01\x80\x01\x00\x00\x00x\x00\x04\xc0\xa8\xbcA\x19ShellyPro4PM-94B97EC07650\x05local\x00\x00/\x80\x01\x00\x00\x00x\x00$\x19ShellyPro4PM-94B97EC07650\x05local\x00\x00\x01@'  # noqa: E501
    protocol.datagram_received(packet, ('127.0.0.1', 6503))
    await browser.async_cancel()
    await aiozc.async_close()

    assert callbacks == [
        ('add', '_http._tcp.local.', 'ShellyPro4PM-94B97EC07650._http._tcp.local.'),
        ('update', '_http._tcp.local.', 'ShellyPro4PM-94B97EC07650._http._tcp.local.'),
    ]


@pytest.mark.asyncio
async def test_service_browser_does_not_try_to_send_if_not_ready():
    """Test that the service browser does not try to send if not ready when rescheduling a type."""
    service_added = asyncio.Event()
    type_ = "_http._tcp.local."
    registration_name = "nosend.%s" % type_

    def on_service_state_change(zeroconf, service_type, state_change, name):
        if name == registration_name:
            if state_change is ServiceStateChange.Added:
                service_added.set()

    aiozc = AsyncZeroconf(interfaces=['127.0.0.1'])
    zeroconf_browser = aiozc.zeroconf
    await zeroconf_browser.async_wait_for_start()

    expected_ttl = const._DNS_HOST_TTL
    time_offset = 0.0

    def _new_current_time_millis():
        """Current system time in milliseconds"""
        return (time.monotonic() * 1000) + (time_offset * 1000)

    assert len(zeroconf_browser.engine.protocols) == 2

    aio_zeroconf_registrar = AsyncZeroconf(interfaces=['127.0.0.1'])
    zeroconf_registrar = aio_zeroconf_registrar.zeroconf
    await aio_zeroconf_registrar.zeroconf.async_wait_for_start()
    assert len(zeroconf_registrar.engine.protocols) == 2
    with patch("zeroconf._services.browser.current_time_millis", _new_current_time_millis):
        service_added = asyncio.Event()
        browser = AsyncServiceBrowser(zeroconf_browser, type_, [on_service_state_change])
        desc = {'path': '/~paulsm/'}
        info = ServiceInfo(
            type_, registration_name, 80, 0, 0, desc, "ash-2.local.", addresses=[socket.inet_aton("10.0.1.2")]
        )
        task = await aio_zeroconf_registrar.async_register_service(info)
        await task

        try:
            await asyncio.wait_for(service_added.wait(), 1)
            time_offset = 1000 * expected_ttl  # set the time to the end of the ttl
            now = _new_current_time_millis()
            browser.query_scheduler._next_time[type_] = now + (1000 * expected_ttl)
            # Make sure the query schedule is to a time in the future
            # so we will reschedule
            with patch.object(
                browser, "_async_send_ready_queries"
            ) as _async_send_ready_queries, patch.object(
                browser, "_async_send_ready_queries_schedule_next"
            ) as _async_send_ready_queries_schedule_next:
                # Reschedule the type to be sent in 1ms in the future
                # to make sure the query is not sent
                browser.reschedule_type(type_, now, now + 1)
                assert not _async_send_ready_queries.called
                await asyncio.sleep(0.01)
                # Make sure it does happen after the sleep
                assert _async_send_ready_queries_schedule_next.called
        finally:
            await aio_zeroconf_registrar.async_close()
            await browser.async_cancel()
            await aiozc.async_close()
