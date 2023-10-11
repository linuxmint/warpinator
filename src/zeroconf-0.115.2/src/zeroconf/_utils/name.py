""" Multicast DNS Service Discovery for Python, v0.14-wmcbrine
    Copyright 2003 Paul Scott-Murphy, 2014 William McBrine

    This module provides a framework for the use of DNS Service Discovery
    using IP multicast.

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
    USA
"""

from functools import lru_cache
from typing import Set

from .._exceptions import BadTypeInNameException
from ..const import (
    _HAS_A_TO_Z,
    _HAS_ASCII_CONTROL_CHARS,
    _HAS_ONLY_A_TO_Z_NUM_HYPHEN,
    _HAS_ONLY_A_TO_Z_NUM_HYPHEN_UNDERSCORE,
    _LOCAL_TRAILER,
    _NONTCP_PROTOCOL_LOCAL_TRAILER,
    _TCP_PROTOCOL_LOCAL_TRAILER,
)


@lru_cache(maxsize=512)
def service_type_name(type_: str, *, strict: bool = True) -> str:  # pylint: disable=too-many-branches
    """
    Validate a fully qualified service name, instance or subtype. [rfc6763]

    Returns fully qualified service name.

    Domain names used by mDNS-SD take the following forms:

                   <sn> . <_tcp|_udp> . local.
      <Instance> . <sn> . <_tcp|_udp> . local.
      <sub>._sub . <sn> . <_tcp|_udp> . local.

    1) must end with 'local.'

      This is true because we are implementing mDNS and since the 'm' means
      multi-cast, the 'local.' domain is mandatory.

    2) local is preceded with either '_udp.' or '_tcp.' unless
       strict is False

    3) service name <sn> precedes <_tcp|_udp> unless
       strict is False

      The rules for Service Names [RFC6335] state that they may be no more
      than fifteen characters long (not counting the mandatory underscore),
      consisting of only letters, digits, and hyphens, must begin and end
      with a letter or digit, must not contain consecutive hyphens, and
      must contain at least one letter.

    The instance name <Instance> and sub type <sub> may be up to 63 bytes.

    The portion of the Service Instance Name is a user-
    friendly name consisting of arbitrary Net-Unicode text [RFC5198]. It
    MUST NOT contain ASCII control characters (byte values 0x00-0x1F and
    0x7F) [RFC20] but otherwise is allowed to contain any characters,
    without restriction, including spaces, uppercase, lowercase,
    punctuation -- including dots -- accented characters, non-Roman text,
    and anything else that may be represented using Net-Unicode.

    :param type_: Type, SubType or service name to validate
    :return: fully qualified service name (eg: _http._tcp.local.)
    """
    if len(type_) > 256:
        # https://datatracker.ietf.org/doc/html/rfc6763#section-7.2
        raise BadTypeInNameException("Full name (%s) must be > 256 bytes" % type_)

    if type_.endswith((_TCP_PROTOCOL_LOCAL_TRAILER, _NONTCP_PROTOCOL_LOCAL_TRAILER)):
        remaining = type_[: -len(_TCP_PROTOCOL_LOCAL_TRAILER)].split('.')
        trailer = type_[-len(_TCP_PROTOCOL_LOCAL_TRAILER) :]
        has_protocol = True
    elif strict:
        raise BadTypeInNameException(
            "Type '%s' must end with '%s' or '%s'"
            % (type_, _TCP_PROTOCOL_LOCAL_TRAILER, _NONTCP_PROTOCOL_LOCAL_TRAILER)
        )
    elif type_.endswith(_LOCAL_TRAILER):
        remaining = type_[: -len(_LOCAL_TRAILER)].split('.')
        trailer = type_[-len(_LOCAL_TRAILER) + 1 :]
        has_protocol = False
    else:
        raise BadTypeInNameException(f"Type '{type_}' must end with '{_LOCAL_TRAILER}'")

    if strict or has_protocol:
        service_name = remaining.pop()
        if not service_name:
            raise BadTypeInNameException("No Service name found")

        if len(remaining) == 1 and len(remaining[0]) == 0:
            raise BadTypeInNameException("Type '%s' must not start with '.'" % type_)

        if service_name[0] != '_':
            raise BadTypeInNameException("Service name (%s) must start with '_'" % service_name)

        test_service_name = service_name[1:]

        if strict and len(test_service_name) > 15:
            # https://datatracker.ietf.org/doc/html/rfc6763#section-7.2
            raise BadTypeInNameException("Service name (%s) must be <= 15 bytes" % test_service_name)

        if '--' in test_service_name:
            raise BadTypeInNameException("Service name (%s) must not contain '--'" % test_service_name)

        if '-' in (test_service_name[0], test_service_name[-1]):
            raise BadTypeInNameException(
                "Service name (%s) may not start or end with '-'" % test_service_name
            )

        if not _HAS_A_TO_Z.search(test_service_name):
            raise BadTypeInNameException(
                "Service name (%s) must contain at least one letter (eg: 'A-Z')" % test_service_name
            )

        allowed_characters_re = (
            _HAS_ONLY_A_TO_Z_NUM_HYPHEN if strict else _HAS_ONLY_A_TO_Z_NUM_HYPHEN_UNDERSCORE
        )

        if not allowed_characters_re.search(test_service_name):
            raise BadTypeInNameException(
                "Service name (%s) must contain only these characters: "
                "A-Z, a-z, 0-9, hyphen ('-')%s" % (test_service_name, "" if strict else ", underscore ('_')")
            )
    else:
        service_name = ''

    if remaining and remaining[-1] == '_sub':
        remaining.pop()
        if len(remaining) == 0 or len(remaining[0]) == 0:
            raise BadTypeInNameException("_sub requires a subtype name")

    if len(remaining) > 1:
        remaining = ['.'.join(remaining)]

    if remaining:
        length = len(remaining[0].encode('utf-8'))
        if length > 63:
            raise BadTypeInNameException("Too long: '%s'" % remaining[0])

        if _HAS_ASCII_CONTROL_CHARS.search(remaining[0]):
            raise BadTypeInNameException(
                "Ascii control character 0x00-0x1F and 0x7F illegal in '%s'" % remaining[0]
            )

    return service_name + trailer


def possible_types(name: str) -> Set[str]:
    """Build a set of all possible types from a fully qualified name."""
    labels = name.split('.')
    label_count = len(labels)
    types = set()
    for count in range(label_count):
        parts = labels[label_count - count - 4 :]
        if not parts[0].startswith('_'):
            break
        types.add('.'.join(parts))
    return types


cached_possible_types = lru_cache(maxsize=256)(possible_types)
