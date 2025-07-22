"""conftest for zeroconf tests."""

from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from zeroconf import _core, const
from zeroconf._handlers import query_handler


@pytest.fixture(autouse=True)
def verify_threads_ended():
    """Verify that the threads are not running after the test."""
    threads_before = frozenset(threading.enumerate())
    yield
    threads = frozenset(threading.enumerate()) - threads_before
    assert not threads


@pytest.fixture
def run_isolated():
    """Change the mDNS port to run the test in isolation."""
    with (
        patch.object(query_handler, "_MDNS_PORT", 5454),
        patch.object(_core, "_MDNS_PORT", 5454),
        patch.object(const, "_MDNS_PORT", 5454),
    ):
        yield


@pytest.fixture
def disable_duplicate_packet_suppression():
    """Disable duplicate packet suppress.

    Some tests run too slowly because of the duplicate
    packet suppression.
    """
    with patch.object(const, "_DUPLICATE_PACKET_SUPPRESSION_INTERVAL", 0):
        yield
