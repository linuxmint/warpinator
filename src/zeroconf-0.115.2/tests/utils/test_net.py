#!/usr/bin/env python


"""Unit tests for zeroconf._utils.net."""
import errno
import socket
import unittest
from unittest.mock import MagicMock, Mock, patch

import ifaddr
import pytest

import zeroconf as r
from zeroconf._utils import net as netutils


def _generate_mock_adapters():
    mock_lo0 = Mock(spec=ifaddr.Adapter)
    mock_lo0.nice_name = "lo0"
    mock_lo0.ips = [ifaddr.IP("127.0.0.1", 8, "lo0")]
    mock_lo0.index = 0
    mock_eth0 = Mock(spec=ifaddr.Adapter)
    mock_eth0.nice_name = "eth0"
    mock_eth0.ips = [ifaddr.IP(("2001:db8::", 1, 1), 8, "eth0")]
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


def test_ip6_to_address_and_index():
    """Test we can extract from mocked adapters."""
    adapters = _generate_mock_adapters()
    assert netutils.ip6_to_address_and_index(adapters, "2001:db8::") == (('2001:db8::', 1, 1), 1)
    assert netutils.ip6_to_address_and_index(adapters, "2001:db8::%1") == (('2001:db8::', 1, 1), 1)
    with pytest.raises(RuntimeError):
        assert netutils.ip6_to_address_and_index(adapters, "2005:db8::")


def test_interface_index_to_ip6_address():
    """Test we can extract from mocked adapters."""
    adapters = _generate_mock_adapters()
    assert netutils.interface_index_to_ip6_address(adapters, 1) == ('2001:db8::', 1, 1)

    # call with invalid adapter
    with pytest.raises(RuntimeError):
        assert netutils.interface_index_to_ip6_address(adapters, 6)

    # call with adapter that has ipv4 address only
    with pytest.raises(RuntimeError):
        assert netutils.interface_index_to_ip6_address(adapters, 2)


def test_ip6_addresses_to_indexes():
    """Test we can extract from mocked adapters."""
    interfaces = [1]
    with patch("zeroconf._utils.net.ifaddr.get_adapters", return_value=_generate_mock_adapters()):
        assert netutils.ip6_addresses_to_indexes(interfaces) == [(('2001:db8::', 1, 1), 1)]

    interfaces_2 = ['2001:db8::']
    with patch("zeroconf._utils.net.ifaddr.get_adapters", return_value=_generate_mock_adapters()):
        assert netutils.ip6_addresses_to_indexes(interfaces_2) == [(('2001:db8::', 1, 1), 1)]


def test_normalize_interface_choice_errors():
    """Test we generate exception on invalid input."""
    with patch("zeroconf._utils.net.get_all_addresses", return_value=[]), patch(
        "zeroconf._utils.net.get_all_addresses_v6", return_value=[]
    ), pytest.raises(RuntimeError):
        netutils.normalize_interface_choice(r.InterfaceChoice.All)

    with pytest.raises(TypeError):
        netutils.normalize_interface_choice("1.2.3.4")


@pytest.mark.parametrize(
    "errno,expected_result",
    [(errno.EADDRINUSE, False), (errno.EADDRNOTAVAIL, False), (errno.EINVAL, False), (0, True)],
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
        nonlocal errors_logged
        errors_logged.append(args)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with pytest.raises(OSError), patch.object(netutils.log, "error", _log_error), patch(
        "socket.socket.setsockopt", side_effect=OSError
    ):
        netutils.disable_ipv6_only_or_raise(sock)

    assert (
        errors_logged[0][0]
        == 'Support for dual V4-V6 sockets is not present, use IPVersion.V4 or IPVersion.V6'
    )


@pytest.mark.skipif(not hasattr(socket, 'SO_REUSEPORT'), reason="System does not have SO_REUSEPORT")
def test_set_so_reuseport_if_available_is_present():
    """Test that setting socket.SO_REUSEPORT only OSError errno.ENOPROTOOPT is trapped."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with pytest.raises(OSError), patch("socket.socket.setsockopt", side_effect=OSError):
        netutils.set_so_reuseport_if_available(sock)

    with patch("socket.socket.setsockopt", side_effect=OSError(errno.ENOPROTOOPT, None)):
        netutils.set_so_reuseport_if_available(sock)


@pytest.mark.skipif(hasattr(socket, 'SO_REUSEPORT'), reason="System has SO_REUSEPORT")
def test_set_so_reuseport_if_available_not_present():
    """Test that we do not try to set SO_REUSEPORT if it is not present."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with patch("socket.socket.setsockopt", side_effect=OSError):
        netutils.set_so_reuseport_if_available(sock)


def test_set_mdns_port_socket_options_for_ip_version():
    """Test OSError with errno with EINVAL and bind address '' from setsockopt IP_MULTICAST_TTL does not raise."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Should raise on EPERM always
    with pytest.raises(OSError), patch("socket.socket.setsockopt", side_effect=OSError(errno.EPERM, None)):
        netutils.set_mdns_port_socket_options_for_ip_version(sock, ('',), r.IPVersion.V4Only)

    # Should raise on EINVAL always when bind address is not ''
    with pytest.raises(OSError), patch("socket.socket.setsockopt", side_effect=OSError(errno.EINVAL, None)):
        netutils.set_mdns_port_socket_options_for_ip_version(sock, ('127.0.0.1',), r.IPVersion.V4Only)

    # Should not raise on EINVAL when bind address is ''
    with patch("socket.socket.setsockopt", side_effect=OSError(errno.EINVAL, None)):
        netutils.set_mdns_port_socket_options_for_ip_version(sock, ('',), r.IPVersion.V4Only)


def test_add_multicast_member():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interface = '127.0.0.1'

    # EPERM should always raise
    with pytest.raises(OSError), patch("socket.socket.setsockopt", side_effect=OSError(errno.EPERM, None)):
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
    with pytest.raises(OSError), patch("socket.socket.setsockopt", side_effect=OSError(errno.ENODEV, None)):
        netutils.add_multicast_member(sock, interface) is False

    # ENODEV should return False for ipv6
    with patch("socket.socket.setsockopt", side_effect=OSError(errno.ENODEV, None)):
        assert netutils.add_multicast_member(sock, ('2001:db8::', 1, 1)) is False  # type: ignore[arg-type]

    # No IPv6 support should return False for IPv6
    with patch("socket.inet_pton", side_effect=OSError()):
        assert netutils.add_multicast_member(sock, ('2001:db8::', 1, 1)) is False  # type: ignore[arg-type]

    # No error should return True
    with patch("socket.socket.setsockopt"):
        assert netutils.add_multicast_member(sock, interface) is True


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


def test_new_respond_socket_new_socket_returns_none():
    """Test new_respond_socket returns None if new_socket returns None."""
    with patch.object(netutils, "new_socket", return_value=None):
        assert netutils.new_respond_socket(("0.0.0.0", 0)) is None  # type: ignore[arg-type]
