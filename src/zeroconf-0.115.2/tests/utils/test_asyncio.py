#!/usr/bin/env python


"""Unit tests for zeroconf._utils.asyncio."""

import asyncio
import concurrent.futures
import contextlib
import threading
import time
from typing import Optional
from unittest.mock import patch

import pytest

from zeroconf import EventLoopBlocked
from zeroconf._engine import _CLOSE_TIMEOUT
from zeroconf._utils import asyncio as aioutils
from zeroconf.const import _LOADED_SYSTEM_TIMEOUT


@pytest.mark.asyncio
async def test_async_get_all_tasks() -> None:
    """Test we can get all tasks in the event loop.

    We make sure we handle RuntimeError here as
    this is not thread safe under PyPy
    """
    loop = aioutils.get_running_loop()
    assert loop is not None
    await aioutils._async_get_all_tasks(loop)
    if not hasattr(asyncio, 'all_tasks'):
        return
    with patch("zeroconf._utils.asyncio.asyncio.all_tasks", side_effect=RuntimeError):
        await aioutils._async_get_all_tasks(loop)


@pytest.mark.asyncio
async def test_get_running_loop_from_async() -> None:
    """Test we can get the event loop."""
    assert isinstance(aioutils.get_running_loop(), asyncio.AbstractEventLoop)


def test_get_running_loop_no_loop() -> None:
    """Test we get None when there is no loop running."""
    assert aioutils.get_running_loop() is None


@pytest.mark.asyncio
async def test_wait_event_or_timeout_times_out() -> None:
    """Test wait_event_or_timeout will timeout."""
    test_event = asyncio.Event()
    await aioutils.wait_event_or_timeout(test_event, 0.1)

    task = asyncio.ensure_future(test_event.wait())
    await asyncio.sleep(0.1)

    async def _async_wait_or_timeout():
        await aioutils.wait_event_or_timeout(test_event, 0.1)

    # Test high lock contention
    await asyncio.gather(*[_async_wait_or_timeout() for _ in range(100)])

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def test_shutdown_loop() -> None:
    """Test shutting down an event loop."""
    loop = None
    loop_thread_ready = threading.Event()
    runcoro_thread_ready = threading.Event()

    def _run_loop() -> None:
        nonlocal loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_thread_ready.set()
        loop.run_forever()

    loop_thread = threading.Thread(target=_run_loop, daemon=True)
    loop_thread.start()
    loop_thread_ready.wait()

    async def _still_running():
        await asyncio.sleep(5)

    def _run_coro() -> None:
        runcoro_thread_ready.set()
        assert loop is not None
        with contextlib.suppress(concurrent.futures.TimeoutError):
            asyncio.run_coroutine_threadsafe(_still_running(), loop).result(1)

    runcoro_thread = threading.Thread(target=_run_coro, daemon=True)
    runcoro_thread.start()
    runcoro_thread_ready.wait()

    time.sleep(0.1)
    assert loop is not None
    aioutils.shutdown_loop(loop)
    for _ in range(5):
        if not loop.is_running():
            break
        time.sleep(0.05)

    assert loop.is_running() is False
    runcoro_thread.join()


def test_cumulative_timeouts_less_than_close_plus_buffer():
    """Test that the combined async timeouts are shorter than the close timeout with the buffer.

    We want to make sure that the close timeout is the one that gets
    raised if something goes wrong.
    """
    assert (
        aioutils._TASK_AWAIT_TIMEOUT + aioutils._GET_ALL_TASKS_TIMEOUT + aioutils._WAIT_FOR_LOOP_TASKS_TIMEOUT
    ) < 1 + _CLOSE_TIMEOUT + _LOADED_SYSTEM_TIMEOUT


@pytest.mark.asyncio
async def test_run_coro_with_timeout() -> None:
    """Test running a coroutine with a timeout raises EventLoopBlocked."""
    loop = asyncio.get_event_loop()
    task: Optional[asyncio.Task] = None

    async def _saved_sleep_task():
        nonlocal task
        task = asyncio.create_task(asyncio.sleep(0.2))
        assert task is not None
        await task

    def _run_in_loop():
        aioutils.run_coro_with_timeout(_saved_sleep_task(), loop, 0.1)

    with pytest.raises(EventLoopBlocked), patch.object(aioutils, "_LOADED_SYSTEM_TIMEOUT", 0.0):
        await loop.run_in_executor(None, _run_in_loop)

    assert task is not None
    # ensure the thread is shutdown
    task.cancel()
    await asyncio.sleep(0)
    await _shutdown_default_executor(loop)


# Remove this when we drop support for older python versions
# since we can use loop.shutdown_default_executor() in 3.9+
async def _shutdown_default_executor(loop: asyncio.AbstractEventLoop) -> None:
    """Backport of cpython 3.9 schedule the shutdown of the default executor."""
    future = loop.create_future()

    def _do_shutdown() -> None:
        try:
            loop._default_executor.shutdown(wait=True)  # type: ignore  # pylint: disable=protected-access
            loop.call_soon_threadsafe(future.set_result, None)
        except Exception as ex:  # pylint: disable=broad-except
            loop.call_soon_threadsafe(future.set_exception, ex)

    thread = threading.Thread(target=_do_shutdown)
    thread.start()
    try:
        await future
    finally:
        thread.join()
