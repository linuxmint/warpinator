"""Unit tests for zeroconf._utils.net."""

from __future__ import annotations

import errno
import socket
import sys
import unittest
import warnings
from unittest.mock import MagicMock, Mock, call, patch

import ifaddr
import pytest

import zeroconf as r
from zeroconf import get_all_addresses, get_all_addresses_v6
from zeroconf._utils import net as netutils


def _generate_mock_adapters():
    mock_lo0 = Mock(spec=ifaddr.Adapter)
    mock_lo0.nice_name = "lo0"
    mock_lo0.ips = [ifaddr.IP("127.0.0.1", 8, "lo0"), ifaddr.IP(("::1", 0, 0), 128, "lo")]
    mock_lo0.index = 0
    mock_eth0 = Mock(spec=ifaddr.Adapter)
    mock_eth0.nice_name = "eth0"
    mock_eth0.ips = [ifaddr.IP(("2001:db8::", 1, 1), 8, "eth0"), ifaddr.IP(("fd00:db8::", 1, 1), 8, "eth0")]
    mock_eth0.index = 1
    mock_eth1 = Mock(spec=ifaddr.Adapter)
    mock_eth1.nice_name = "eth1"
    mock_eth1.ips = [ifaddr.IP("192.168.1.5", 23, "eth1")]
    mock_eth1.index = 2
    mock_vtun0 = Mock(spec=ifaddr.Adapter)
    mock_vtun0.nice_name = "vtun0"
    mock_vtun0.ips = [ifaddr.IP("169.254.3.2", 16, "vtun0")]
    mock_vtun0.index = 3
    return [mock_eth0, mock_lo0, mock_eth1, mock_vtun0]


def test_get_all_addresses() -> None:
    """Test public get_all_addresses API."""
    with (
        patch(
            "zeroconf._utils.net.ifaddr.get_adapters",
            return_value=_generate_mock_adapters(),
        ),
        warnings.catch_warnings(record=True) as warned,
    ):
        addresses = get_all_addresses()
        assert isinstance(addresses, list)
        assert len(addresses) == 3
        assert len(warned) == 1
        first_warning = warned[0]
        assert "get_all_addresses is deprecated" in str(first_warning.message)


def test_get_all_addresses_v6() -> None:
    """Test public get_all_addresses_v6 API."""
    with (
        patch(
            "zeroconf._utils.net.ifaddr.get_adapters",
            return_value=_generate_mock_adapters(),
        ),
        warnings.catch_warnings(record=True) as warned,
    ):
        addresses = get_all_addresses_v6()
        assert isinstance(addresses, list)
        assert len(addresses) == 3
        assert len(warned) == 1
        first_warning = warned[0]
        assert "get_all_addresses_v6 is deprecated" in str(first_warning.message)


def test_ip6_to_address_and_index():
    """Test we can extract from mocked adapters."""
    adapters = _generate_mock_adapters()
    assert netutils.ip6_to_address_and_index(adapters, "2001:db8::") == (
        ("2001:db8::", 1, 1),
        1,
    )
    assert netutils.ip6_to_address_and_index(adapters, "2001:db8::%1") == (
        ("2001:db8::", 1, 1),
        1,
    )
    with pytest.raises(RuntimeError):
        assert netutils.ip6_to_address_and_index(adapters, "2005:db8::")


def test_interface_index_to_ip6_address():
    """Test we can extract from mocked adapters."""
    adapters = _generate_mock_adapters()
    assert netutils.interface_index_to_ip6_address(adapters, 1) == ("2001:db8::", 1, 1)

    # call with invalid adapter
    with pytest.raises(RuntimeError):
        assert netutils.interface_index_to_ip6_address(adapters, 6)

    # call with adapter that has ipv4 address only
    with pytest.raises(RuntimeError):
        assert netutils.interface_index_to_ip6_address(adapters, 2)


def test_ip6_addresses_to_indexes():
    """Test we can extract from mocked adapters."""
    interfaces = [1]
    with patch(
        "zeroconf._utils.net.ifaddr.get_adapters",
        return_value=_generate_mock_adapters(),
    ):
        assert netutils.ip6_addresses_to_indexes(interfaces) == [(("2001:db8::", 1, 1), 1)]

    interfaces_2 = ["2001:db8::"]
    with patch(
        "zeroconf._utils.net.ifaddr.get_adapters",
        return_value=_generate_mock_adapters(),
    ):
        assert netutils.ip6_addresses_to_indexes(interfaces_2) == [(("2001:db8::", 1, 1), 1)]


def test_normalize_interface_choice_errors():
    """Test we generate exception on invalid input."""
    with (
        patch("zeroconf._utils.net.get_all_addresses_ipv4", return_value=[]),
        patch("zeroconf._utils.net.get_all_addresses_ipv6", return_value=[]),
        pytest.raises(RuntimeError),
    ):
        netutils.normalize_interface_choice(r.InterfaceChoice.All)

    with pytest.raises(TypeError):
        netutils.normalize_interface_choice("1.2.3.4")


@pytest.mark.parametrize(
    "errno,expected_result",
    [
        (errno.EADDRINUSE, False),
        (errno.EADDRNOTAVAIL, False),
        (errno.EINVAL, False),
        (0, True),
    ],
)
def test_add_multicast_member_socket_errors(errno, expected_result):
    """Test we handle socket errors when adding multicast members."""
    if errno:
        setsockopt_mock = unittest.mock.Mock(side_effect=OSError(errno, f"Error: {errno}"))
    else:
        setsockopt_mock = unittest.mock.Mock()
    fileno_mock = unittest.mock.PropertyMock(return_value=10)
    socket_mock = unittest.mock.Mock(setsockopt=setsockopt_mock, fileno=fileno_mock)
    assert r.add_multicast_member(socket_mock, "0.0.0.0") == expected_result


def test_autodetect_ip_version():
    """Tests for auto detecting IPVersion based on interface ips."""
    assert r.autodetect_ip_version(["1.3.4.5"]) is r.IPVersion.V4Only
    assert r.autodetect_ip_version([]) is r.IPVersion.V4Only
    assert r.autodetect_ip_version(["::1", "1.2.3.4"]) is r.IPVersion.All
    assert r.autodetect_ip_version(["::1"]) is r.IPVersion.V6Only


def test_disable_ipv6_only_or_raise():
    """Test that IPV6_V6ONLY failing logs a nice error message and still raises."""
    errors_logged = []

    def _log_error(*args):
        errors_logged.append(args)

    with (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock,
        pytest.raises(OSError),
        patch.object(netutils.log, "error", _log_error),
        patch("socket.socket.setsockopt", side_effect=OSError),
    ):
        netutils.disable_ipv6_only_or_raise(sock)

    assert (
        errors_logged[0][0]
        == "Support for dual V4-V6 sockets is not present, use IPVersion.V4 or IPVersion.V6"
    )


@pytest.mark.skipif(not hasattr(socket, "SO_REUSEPORT"), reason="System does not have SO_REUSEPORT")
def test_set_so_reuseport_if_available_is_present():
    """Test that setting socket.SO_REUSEPORT only OSError errno.ENOPROTOOPT is trapped."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        with pytest.raises(OSError), patch("socket.socket.setsockopt", side_effect=OSError):
            netutils.set_so_reuseport_if_available(sock)

        with patch("socket.socket.setsockopt", side_effect=OSError(errno.ENOPROTOOPT, None)):
            netutils.set_so_reuseport_if_available(sock)


@pytest.mark.skipif(hasattr(socket, "SO_REUSEPORT"), reason="System has SO_REUSEPORT")
def test_set_so_reuseport_if_available_not_present():
    """Test that we do not try to set SO_REUSEPORT if it is not present."""
    with (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock,
        patch("socket.socket.setsockopt", side_effect=OSError),
    ):
        netutils.set_so_reuseport_if_available(sock)


def test_set_respond_socket_multicast_options():
    """Test OSError with errno with EINVAL and bind address ''.

    from setsockopt IP_MULTICAST_TTL does not raise."""
    # Should raise on EINVAL always
    with (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock,
        pytest.raises(OSError),
        patch("socket.socket.setsockopt", side_effect=OSError(errno.EINVAL, None)),
    ):
        netutils.set_respond_socket_multicast_options(sock, r.IPVersion.V4Only)

    with pytest.raises(RuntimeError):
        netutils.set_respond_socket_multicast_options(sock, r.IPVersion.All)


def test_add_multicast_member(caplog: pytest.LogCaptureFixture) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        interface = "127.0.0.1"

        # EPERM should always raise
        with (
            pytest.raises(OSError),
            patch("socket.socket.setsockopt", side_effect=OSError(errno.EPERM, None)),
        ):
            netutils.add_multicast_member(sock, interface)

        # EADDRINUSE should return False
        with patch("socket.socket.setsockopt", side_effect=OSError(errno.EADDRINUSE, None)):
            assert netutils.add_multicast_member(sock, interface) is False

        # EADDRNOTAVAIL should return False
        with patch("socket.socket.setsockopt", side_effect=OSError(errno.EADDRNOTAVAIL, None)):
            assert netutils.add_multicast_member(sock, interface) is False

        # EINVAL should return False
        with patch("socket.socket.setsockopt", side_effect=OSError(errno.EINVAL, None)):
            assert netutils.add_multicast_member(sock, interface) is False

        # ENOPROTOOPT should return False
        with patch("socket.socket.setsockopt", side_effect=OSError(errno.ENOPROTOOPT, None)):
            assert netutils.add_multicast_member(sock, interface) is False

        # ENODEV should raise for ipv4
        with (
            pytest.raises(OSError),
            patch("socket.socket.setsockopt", side_effect=OSError(errno.ENODEV, None)),
        ):
            assert netutils.add_multicast_member(sock, interface) is False

        # ENODEV should return False for ipv6
        with patch("socket.socket.setsockopt", side_effect=OSError(errno.ENODEV, None)):
            assert netutils.add_multicast_member(sock, ("2001:db8::", 1, 1)) is False  # type: ignore[arg-type]

        # No IPv6 support should return False for IPv6
        with patch("socket.inet_pton", side_effect=OSError()):
            assert netutils.add_multicast_member(sock, ("2001:db8::", 1, 1)) is False  # type: ignore[arg-type]

        # No error should return True
        with patch("socket.socket.setsockopt"):
            assert netutils.add_multicast_member(sock, interface) is True

        # Ran out of IGMP memberships is forgiving and logs about igmp_max_memberships on linux
        caplog.clear()
        with (
            patch.object(sys, "platform", "linux"),
            patch(
                "socket.socket.setsockopt", side_effect=OSError(errno.ENOBUFS, "No buffer space available")
            ),
        ):
            assert netutils.add_multicast_member(sock, interface) is False
            assert "No buffer space available" in caplog.text
            assert "net.ipv4.igmp_max_memberships" in caplog.text

        # Ran out of IGMP memberships is forgiving and logs
        caplog.clear()
        with (
            patch.object(sys, "platform", "darwin"),
            patch(
                "socket.socket.setsockopt", side_effect=OSError(errno.ENOBUFS, "No buffer space available")
            ),
        ):
            assert netutils.add_multicast_member(sock, interface) is False
            assert "No buffer space available" in caplog.text
            assert "net.ipv4.igmp_max_memberships" not in caplog.text


def test_bind_raises_skips_address():
    """Test bind failing in new_socket returns None on EADDRNOTAVAIL."""
    err = errno.EADDRNOTAVAIL

    def _mock_socket(*args, **kwargs):
        sock = MagicMock()
        sock.bind = MagicMock(side_effect=OSError(err, f"Error: {err}"))
        return sock

    with patch("socket.socket", _mock_socket):
        assert netutils.new_socket(("0.0.0.0", 0)) is None  # type: ignore[arg-type]

    err = errno.EAGAIN
    with pytest.raises(OSError), patch("socket.socket", _mock_socket):
        netutils.new_socket(("0.0.0.0", 0))  # type: ignore[arg-type]


def test_bind_raises_address_in_use(caplog: pytest.LogCaptureFixture) -> None:
    """Test bind failing in new_socket returns None on EADDRINUSE."""

    def _mock_socket(*args, **kwargs):
        sock = MagicMock()
        sock.bind = MagicMock(side_effect=OSError(errno.EADDRINUSE, f"Error: {errno.EADDRINUSE}"))
        return sock

    with (
        pytest.raises(OSError),
        patch.object(sys, "platform", "darwin"),
        patch("socket.socket", _mock_socket),
    ):
        netutils.new_socket(("0.0.0.0", 0))  # type: ignore[arg-type]
    assert (
        "On BSD based systems sharing the same port with "
        "another stack may require processes to run with the same UID"
    ) in caplog.text
    assert (
        "When using avahi, make sure disallow-other-stacks is set to no in avahi-daemon.conf" in caplog.text
    )

    caplog.clear()
    with pytest.raises(OSError), patch.object(sys, "platform", "linux"), patch("socket.socket", _mock_socket):
        netutils.new_socket(("0.0.0.0", 0))  # type: ignore[arg-type]
    assert (
        "On BSD based systems sharing the same port with "
        "another stack may require processes to run with the same UID"
    ) not in caplog.text
    assert (
        "When using avahi, make sure disallow-other-stacks is set to no in avahi-daemon.conf" in caplog.text
    )


def test_new_respond_socket_new_socket_returns_none():
    """Test new_respond_socket returns None if new_socket returns None."""
    with patch.object(netutils, "new_socket", return_value=None):
        assert netutils.new_respond_socket(("0.0.0.0", 0)) is None  # type: ignore[arg-type]


def test_create_sockets_interfaces_all_unicast():
    """Test create_sockets with unicast."""

    with (
        patch("zeroconf._utils.net.new_socket") as mock_new_socket,
        patch(
            "zeroconf._utils.net.ifaddr.get_adapters",
            return_value=_generate_mock_adapters(),
        ),
    ):
        mock_socket = Mock(spec=socket.socket)
        mock_new_socket.return_value = mock_socket

        listen_socket, respond_sockets = r.create_sockets(
            interfaces=r.InterfaceChoice.All, unicast=True, ip_version=r.IPVersion.All
        )

        assert listen_socket is None
        mock_new_socket.assert_any_call(
            port=0,
            ip_version=r.IPVersion.V6Only,
            apple_p2p=False,
            bind_addr=("2001:db8::", 1, 1),
        )
        mock_new_socket.assert_any_call(
            port=0,
            ip_version=r.IPVersion.V4Only,
            apple_p2p=False,
            bind_addr=("192.168.1.5",),
        )


def test_create_sockets_interfaces_all() -> None:
    """Test create_sockets with all interfaces.

    Tests if a responder socket is created for every successful multicast
    join.
    """
    adapters = _generate_mock_adapters()

    # Additional IPv6 addresses usually fail to add membership
    failure_interface = ("fd00:db8::", 1, 1)

    expected_calls = []
    for adapter in adapters:
        for ip in adapter.ips:
            if ip.ip == failure_interface:
                continue

            if ip.is_IPv4:
                bind_addr = (ip.ip,)
                ip_version = r.IPVersion.V4Only
            else:
                bind_addr = ip.ip
                ip_version = r.IPVersion.V6Only

            expected_calls.append(
                call(
                    port=5353,
                    ip_version=ip_version,
                    apple_p2p=False,
                    bind_addr=bind_addr,
                )
            )

    def _patched_add_multicast_member(sock, interface):
        return interface[0] != failure_interface

    with (
        patch("zeroconf._utils.net.new_socket") as mock_new_socket,
        patch(
            "zeroconf._utils.net.ifaddr.get_adapters",
            return_value=adapters,
        ),
        patch("zeroconf._utils.net.add_multicast_member", side_effect=_patched_add_multicast_member),
    ):
        mock_socket = Mock(spec=socket.socket)
        mock_new_socket.return_value = mock_socket

        r.create_sockets(interfaces=r.InterfaceChoice.All, ip_version=r.IPVersion.All)

        def call_to_tuple(c):
            return (c.args, tuple(sorted(c.kwargs.items())))

        # Exclude first new_socket call as this is the listen socket
        actual_calls_set = {call_to_tuple(c) for c in mock_new_socket.call_args_list[1:]}
        expected_calls_set = {call_to_tuple(c) for c in expected_calls}

        assert actual_calls_set == expected_calls_set
