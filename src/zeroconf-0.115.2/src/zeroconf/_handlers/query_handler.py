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


from typing import TYPE_CHECKING, List, Optional, Set, cast

from .._cache import DNSCache, _UniqueRecordsType
from .._dns import DNSAddress, DNSPointer, DNSQuestion, DNSRecord, DNSRRSet
from .._history import QuestionHistory
from .._protocol.incoming import DNSIncoming
from .._services.registry import ServiceRegistry
from .._utils.net import IPVersion
from ..const import (
    _ADDRESS_RECORD_TYPES,
    _CLASS_IN,
    _DNS_OTHER_TTL,
    _ONE_SECOND,
    _SERVICE_TYPE_ENUMERATION_NAME,
    _TYPE_A,
    _TYPE_AAAA,
    _TYPE_ANY,
    _TYPE_NSEC,
    _TYPE_PTR,
    _TYPE_SRV,
    _TYPE_TXT,
)
from .answers import QuestionAnswers, _AnswerWithAdditionalsType

_RESPOND_IMMEDIATE_TYPES = {_TYPE_NSEC, _TYPE_SRV, *_ADDRESS_RECORD_TYPES}

_int = int


class _QueryResponse:
    """A pair for unicast and multicast DNSOutgoing responses."""

    __slots__ = (
        "_is_probe",
        "_questions",
        "_now",
        "_cache",
        "_additionals",
        "_ucast",
        "_mcast_now",
        "_mcast_aggregate",
        "_mcast_aggregate_last_second",
    )

    def __init__(self, cache: DNSCache, questions: List[DNSQuestion], is_probe: bool, now: float) -> None:
        """Build a query response."""
        self._is_probe = is_probe
        self._questions = questions
        self._now = now
        self._cache = cache
        self._additionals: _AnswerWithAdditionalsType = {}
        self._ucast: Set[DNSRecord] = set()
        self._mcast_now: Set[DNSRecord] = set()
        self._mcast_aggregate: Set[DNSRecord] = set()
        self._mcast_aggregate_last_second: Set[DNSRecord] = set()

    def add_qu_question_response(self, answers: _AnswerWithAdditionalsType) -> None:
        """Generate a response to a multicast QU query."""
        for record, additionals in answers.items():
            self._additionals[record] = additionals
            if self._is_probe:
                self._ucast.add(record)
            if not self._has_mcast_within_one_quarter_ttl(record):
                self._mcast_now.add(record)
            elif not self._is_probe:
                self._ucast.add(record)

    def add_ucast_question_response(self, answers: _AnswerWithAdditionalsType) -> None:
        """Generate a response to a unicast query."""
        self._additionals.update(answers)
        self._ucast.update(answers)

    def add_mcast_question_response(self, answers: _AnswerWithAdditionalsType) -> None:
        """Generate a response to a multicast query."""
        self._additionals.update(answers)
        for answer in answers:
            if self._is_probe:
                self._mcast_now.add(answer)
                continue

            if self._has_mcast_record_in_last_second(answer):
                self._mcast_aggregate_last_second.add(answer)
                continue

            if len(self._questions) == 1:
                question = self._questions[0]
                if question.type in _RESPOND_IMMEDIATE_TYPES:
                    self._mcast_now.add(answer)
                    continue

            self._mcast_aggregate.add(answer)

    def answers(
        self,
    ) -> QuestionAnswers:
        """Return answer sets that will be queued."""
        ucast = {r: self._additionals[r] for r in self._ucast}
        mcast_now = {r: self._additionals[r] for r in self._mcast_now}
        mcast_aggregate = {r: self._additionals[r] for r in self._mcast_aggregate}
        mcast_aggregate_last_second = {r: self._additionals[r] for r in self._mcast_aggregate_last_second}
        return QuestionAnswers(ucast, mcast_now, mcast_aggregate, mcast_aggregate_last_second)

    def _has_mcast_within_one_quarter_ttl(self, record: DNSRecord) -> bool:
        """Check to see if a record has been mcasted recently.

        https://datatracker.ietf.org/doc/html/rfc6762#section-5.4
        When receiving a question with the unicast-response bit set, a
        responder SHOULD usually respond with a unicast packet directed back
        to the querier.  However, if the responder has not multicast that
        record recently (within one quarter of its TTL), then the responder
        SHOULD instead multicast the response so as to keep all the peer
        caches up to date
        """
        if TYPE_CHECKING:
            record = cast(_UniqueRecordsType, record)
        maybe_entry = self._cache.async_get_unique(record)
        return bool(maybe_entry and maybe_entry.is_recent(self._now))

    def _has_mcast_record_in_last_second(self, record: DNSRecord) -> bool:
        """Check if an answer was seen in the last second.
        Protect the network against excessive packet flooding
        https://datatracker.ietf.org/doc/html/rfc6762#section-14
        """
        if TYPE_CHECKING:
            record = cast(_UniqueRecordsType, record)
        maybe_entry = self._cache.async_get_unique(record)
        return bool(maybe_entry and self._now - maybe_entry.created < _ONE_SECOND)


class QueryHandler:
    """Query the ServiceRegistry."""

    __slots__ = ("registry", "cache", "question_history")

    def __init__(self, registry: ServiceRegistry, cache: DNSCache, question_history: QuestionHistory) -> None:
        """Init the query handler."""
        self.registry = registry
        self.cache = cache
        self.question_history = question_history

    def _add_service_type_enumeration_query_answers(
        self, answer_set: _AnswerWithAdditionalsType, known_answers: DNSRRSet
    ) -> None:
        """Provide an answer to a service type enumeration query.

        https://datatracker.ietf.org/doc/html/rfc6763#section-9
        """
        for stype in self.registry.async_get_types():
            dns_pointer = DNSPointer(
                _SERVICE_TYPE_ENUMERATION_NAME, _TYPE_PTR, _CLASS_IN, _DNS_OTHER_TTL, stype, 0.0
            )
            if not known_answers.suppresses(dns_pointer):
                answer_set[dns_pointer] = set()

    def _add_pointer_answers(
        self, lower_name: str, answer_set: _AnswerWithAdditionalsType, known_answers: DNSRRSet
    ) -> None:
        """Answer PTR/ANY question."""
        for service in self.registry.async_get_infos_type(lower_name):
            # Add recommended additional answers according to
            # https://tools.ietf.org/html/rfc6763#section-12.1.
            dns_pointer = service._dns_pointer(None)
            if known_answers.suppresses(dns_pointer):
                continue
            answer_set[dns_pointer] = {
                service._dns_service(None),
                service._dns_text(None),
            } | service._get_address_and_nsec_records(None)

    def _add_address_answers(
        self,
        lower_name: str,
        answer_set: _AnswerWithAdditionalsType,
        known_answers: DNSRRSet,
        type_: _int,
    ) -> None:
        """Answer A/AAAA/ANY question."""
        for service in self.registry.async_get_infos_server(lower_name):
            answers: List[DNSAddress] = []
            additionals: Set[DNSRecord] = set()
            seen_types: Set[int] = set()
            for dns_address in service._dns_addresses(None, IPVersion.All):
                seen_types.add(dns_address.type)
                if dns_address.type != type_:
                    additionals.add(dns_address)
                elif not known_answers.suppresses(dns_address):
                    answers.append(dns_address)
            missing_types: Set[int] = _ADDRESS_RECORD_TYPES - seen_types
            if answers:
                if missing_types:
                    assert service.server is not None, "Service server must be set for NSEC record."
                    additionals.add(service._dns_nsec(list(missing_types), None))
                for answer in answers:
                    answer_set[answer] = additionals
            elif type_ in missing_types:
                assert service.server is not None, "Service server must be set for NSEC record."
                answer_set[service._dns_nsec(list(missing_types), None)] = set()

    def _answer_question(
        self,
        question: DNSQuestion,
        known_answers: DNSRRSet,
    ) -> _AnswerWithAdditionalsType:
        """Answer a question."""
        answer_set: _AnswerWithAdditionalsType = {}
        question_lower_name = question.name.lower()
        type_ = question.type

        if type_ == _TYPE_PTR and question_lower_name == _SERVICE_TYPE_ENUMERATION_NAME:
            self._add_service_type_enumeration_query_answers(answer_set, known_answers)
            return answer_set

        if type_ in (_TYPE_PTR, _TYPE_ANY):
            self._add_pointer_answers(question_lower_name, answer_set, known_answers)

        if type_ in (_TYPE_A, _TYPE_AAAA, _TYPE_ANY):
            self._add_address_answers(question_lower_name, answer_set, known_answers, type_)

        if type_ in (_TYPE_SRV, _TYPE_TXT, _TYPE_ANY):
            service = self.registry.async_get_info_name(question_lower_name)
            if service is not None:
                if type_ in (_TYPE_SRV, _TYPE_ANY):
                    # Add recommended additional answers according to
                    # https://tools.ietf.org/html/rfc6763#section-12.2.
                    dns_service = service._dns_service(None)
                    if not known_answers.suppresses(dns_service):
                        answer_set[dns_service] = service._get_address_and_nsec_records(None)
                if type_ in (_TYPE_TXT, _TYPE_ANY):
                    dns_text = service._dns_text(None)
                    if not known_answers.suppresses(dns_text):
                        answer_set[dns_text] = set()

        return answer_set

    def async_response(  # pylint: disable=unused-argument
        self, msgs: List[DNSIncoming], ucast_source: bool
    ) -> QuestionAnswers:
        """Deal with incoming query packets. Provides a response if possible.

        This function must be run in the event loop as it is not
        threadsafe.
        """
        answers: List[DNSRecord] = []
        is_probe = False
        msg = msgs[0]
        questions = msg.questions
        now = msg.now
        for msg in msgs:
            if not msg.is_probe():
                answers.extend(msg.answers())
            else:
                is_probe = True
        known_answers = DNSRRSet(answers)
        query_res = _QueryResponse(self.cache, questions, is_probe, now)
        known_answers_set: Optional[Set[DNSRecord]] = None

        for msg in msgs:
            for question in msg.questions:
                if not question.unique:  # unique and unicast are the same flag
                    if not known_answers_set:  # pragma: no branch
                        known_answers_set = known_answers.lookup_set()
                    self.question_history.add_question_at_time(question, now, known_answers_set)
                answer_set = self._answer_question(question, known_answers)
                if not ucast_source and question.unique:  # unique and unicast are the same flag
                    query_res.add_qu_question_response(answer_set)
                    continue
                if ucast_source:
                    query_res.add_ucast_question_response(answer_set)
                # We always multicast as well even if its a unicast
                # source as long as we haven't done it recently (75% of ttl)
                query_res.add_mcast_question_response(answer_set)

        return query_res.answers()
