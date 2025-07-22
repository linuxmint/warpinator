"""Unit tests for zeroconf._utils.name."""

from __future__ import annotations

import socket

import pytest

from zeroconf import BadTypeInNameException
from zeroconf._services.info import ServiceInfo, instance_name_from_service_info
from zeroconf._utils import name as nameutils


def test_service_type_name_overlong_type():
    """Test overlong service_type_name type."""
    with pytest.raises(BadTypeInNameException):
        nameutils.service_type_name("Tivo1._tivo-videostream._tcp.local.")
    nameutils.service_type_name("Tivo1._tivo-videostream._tcp.local.", strict=False)


def test_service_type_name_overlong_full_name():
    """Test overlong service_type_name full name."""
    long_name = "Tivo1Tivo1Tivo1Tivo1Tivo1Tivo1Tivo1Tivo1" * 100
    with pytest.raises(BadTypeInNameException):
        nameutils.service_type_name(f"{long_name}._tivo-videostream._tcp.local.")
    with pytest.raises(BadTypeInNameException):
        nameutils.service_type_name(f"{long_name}._tivo-videostream._tcp.local.", strict=False)


@pytest.mark.parametrize(
    "instance_name, service_type",
    (
        ("CustomerInformationService-F4D4885E9EEB", "_ibisip_http._tcp.local."),
        ("DeviceManagementService_F4D4885E9EEB", "_ibisip_http._tcp.local."),
    ),
)
def test_service_type_name_non_strict_compliant_names(instance_name, service_type):
    """Test service_type_name for valid names, but not strict-compliant."""
    desc = {"path": "/~paulsm/"}
    service_name = f"{instance_name}.{service_type}"
    service_server = "ash-1.local."
    service_address = socket.inet_aton("10.0.1.2")
    info = ServiceInfo(
        service_type,
        service_name,
        22,
        0,
        0,
        desc,
        service_server,
        addresses=[service_address],
    )
    assert info.get_name() == instance_name

    with pytest.raises(BadTypeInNameException):
        nameutils.service_type_name(service_name)
    with pytest.raises(BadTypeInNameException):
        instance_name_from_service_info(info)

    nameutils.service_type_name(service_name, strict=False)
    assert instance_name_from_service_info(info, strict=False) == instance_name


def test_possible_types():
    """Test possible types from name."""
    assert nameutils.possible_types(".") == set()
    assert nameutils.possible_types("local.") == set()
    assert nameutils.possible_types("_tcp.local.") == set()
    assert nameutils.possible_types("_test-srvc-type._tcp.local.") == {"_test-srvc-type._tcp.local."}
    assert nameutils.possible_types("_any._tcp.local.") == {"_any._tcp.local."}
    assert nameutils.possible_types(".._x._tcp.local.") == {"_x._tcp.local."}
    assert nameutils.possible_types("x.y._http._tcp.local.") == {"_http._tcp.local."}
    assert nameutils.possible_types("1.2.3._mqtt._tcp.local.") == {"_mqtt._tcp.local."}
    assert nameutils.possible_types("x.sub._http._tcp.local.") == {"_http._tcp.local."}
    assert nameutils.possible_types("6d86f882b90facee9170ad3439d72a4d6ee9f511._zget._http._tcp.local.") == {
        "_http._tcp.local.",
        "_zget._http._tcp.local.",
    }
    assert nameutils.possible_types("my._printer._sub._http._tcp.local.") == {
        "_http._tcp.local.",
        "_sub._http._tcp.local.",
        "_printer._sub._http._tcp.local.",
    }
