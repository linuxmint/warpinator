#!/usr/bin/env python


"""Unit tests for logger.py."""

import logging
from unittest.mock import call, patch

from zeroconf._logger import QuietLogger, set_logger_level_if_unset


def test_loading_logger():
    """Test loading logger does not change level unless it is unset."""
    log = logging.getLogger('zeroconf')
    log.setLevel(logging.CRITICAL)
    set_logger_level_if_unset()
    log = logging.getLogger('zeroconf')
    assert log.level == logging.CRITICAL

    log = logging.getLogger('zeroconf')
    log.setLevel(logging.NOTSET)
    set_logger_level_if_unset()
    log = logging.getLogger('zeroconf')
    assert log.level == logging.WARNING


def test_log_warning_once():
    """Test we only log with warning level once."""
    QuietLogger._seen_logs = {}
    quiet_logger = QuietLogger()
    with patch("zeroconf._logger.log.warning") as mock_log_warning, patch(
        "zeroconf._logger.log.debug"
    ) as mock_log_debug:
        quiet_logger.log_warning_once("the warning")

    assert mock_log_warning.mock_calls
    assert not mock_log_debug.mock_calls

    with patch("zeroconf._logger.log.warning") as mock_log_warning, patch(
        "zeroconf._logger.log.debug"
    ) as mock_log_debug:
        quiet_logger.log_warning_once("the warning")

    assert not mock_log_warning.mock_calls
    assert mock_log_debug.mock_calls


def test_log_exception_warning():
    """Test we only log with warning level once."""
    QuietLogger._seen_logs = {}
    quiet_logger = QuietLogger()
    with patch("zeroconf._logger.log.warning") as mock_log_warning, patch(
        "zeroconf._logger.log.debug"
    ) as mock_log_debug:
        quiet_logger.log_exception_warning("the exception warning")

    assert mock_log_warning.mock_calls
    assert not mock_log_debug.mock_calls

    with patch("zeroconf._logger.log.warning") as mock_log_warning, patch(
        "zeroconf._logger.log.debug"
    ) as mock_log_debug:
        quiet_logger.log_exception_warning("the exception warning")

    assert not mock_log_warning.mock_calls
    assert mock_log_debug.mock_calls


def test_llog_exception_debug():
    """Test we only log with a trace once."""
    QuietLogger._seen_logs = {}
    quiet_logger = QuietLogger()
    with patch("zeroconf._logger.log.debug") as mock_log_debug:
        quiet_logger.log_exception_debug("the exception")

    assert mock_log_debug.mock_calls == [call('the exception', exc_info=True)]

    with patch("zeroconf._logger.log.debug") as mock_log_debug:
        quiet_logger.log_exception_debug("the exception")

    assert mock_log_debug.mock_calls == [call('the exception', exc_info=False)]


def test_log_exception_once():
    """Test we only log with warning level once."""
    QuietLogger._seen_logs = {}
    quiet_logger = QuietLogger()
    exc = Exception()
    with patch("zeroconf._logger.log.warning") as mock_log_warning, patch(
        "zeroconf._logger.log.debug"
    ) as mock_log_debug:
        quiet_logger.log_exception_once(exc, "the exceptional exception warning")

    assert mock_log_warning.mock_calls
    assert not mock_log_debug.mock_calls

    with patch("zeroconf._logger.log.warning") as mock_log_warning, patch(
        "zeroconf._logger.log.debug"
    ) as mock_log_debug:
        quiet_logger.log_exception_once(exc, "the exceptional exception warning")

    assert not mock_log_warning.mock_calls
    assert mock_log_debug.mock_calls
