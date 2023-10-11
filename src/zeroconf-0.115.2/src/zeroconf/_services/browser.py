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

import asyncio
import queue
import random
import threading
import warnings
from types import TracebackType  # noqa # used in type hints
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from .._dns import DNSPointer, DNSQuestion, DNSQuestionType
from .._logger import log
from .._protocol.outgoing import DNSOutgoing
from .._record_update import RecordUpdate
from .._services import (
    ServiceListener,
    ServiceStateChange,
    Signal,
    SignalRegistrationInterface,
)
from .._updates import RecordUpdateListener
from .._utils.name import cached_possible_types, service_type_name
from .._utils.time import current_time_millis, millis_to_seconds
from ..const import (
    _ADDRESS_RECORD_TYPES,
    _BROWSER_BACKOFF_LIMIT,
    _BROWSER_TIME,
    _CLASS_IN,
    _DNS_PACKET_HEADER_LEN,
    _EXPIRE_REFRESH_TIME_PERCENT,
    _FLAGS_QR_QUERY,
    _MAX_MSG_TYPICAL,
    _MDNS_ADDR,
    _MDNS_ADDR6,
    _MDNS_PORT,
    _TYPE_PTR,
)

# https://datatracker.ietf.org/doc/html/rfc6762#section-5.2
_FIRST_QUERY_DELAY_RANDOM_INTERVAL = (20, 120)  # ms

_ON_CHANGE_DISPATCH = {
    ServiceStateChange.Added: "add_service",
    ServiceStateChange.Removed: "remove_service",
    ServiceStateChange.Updated: "update_service",
}

SERVICE_STATE_CHANGE_ADDED = ServiceStateChange.Added
SERVICE_STATE_CHANGE_REMOVED = ServiceStateChange.Removed
SERVICE_STATE_CHANGE_UPDATED = ServiceStateChange.Updated

if TYPE_CHECKING:
    from .._core import Zeroconf

float_ = float
int_ = int
bool_ = bool
str_ = str

_QuestionWithKnownAnswers = Dict[DNSQuestion, Set[DNSPointer]]


class _DNSPointerOutgoingBucket:
    """A DNSOutgoing bucket."""

    __slots__ = ('now', 'out', 'bytes')

    def __init__(self, now: float, multicast: bool) -> None:
        """Create a bucke to wrap a DNSOutgoing."""
        self.now = now
        self.out = DNSOutgoing(_FLAGS_QR_QUERY, multicast=multicast)
        self.bytes = 0

    def add(self, max_compressed_size: int_, question: DNSQuestion, answers: Set[DNSPointer]) -> None:
        """Add a new set of questions and known answers to the outgoing."""
        self.out.add_question(question)
        for answer in answers:
            self.out.add_answer_at_time(answer, self.now)
        self.bytes += max_compressed_size


def _group_ptr_queries_with_known_answers(
    now: float_, multicast: bool_, question_with_known_answers: _QuestionWithKnownAnswers
) -> List[DNSOutgoing]:
    """Aggregate queries so that as many known answers as possible fit in the same packet
    without having known answers spill over into the next packet unless the
    question and known answers are always going to exceed the packet size.

    Some responders do not implement multi-packet known answer suppression
    so we try to keep all the known answers in the same packet as the
    questions.
    """
    # This is the maximum size the query + known answers can be with name compression.
    # The actual size of the query + known answers may be a bit smaller since other
    # parts may be shared when the final DNSOutgoing packets are constructed. The
    # goal of this algorithm is to quickly bucket the query + known answers without
    # the overhead of actually constructing the packets.
    query_by_size: Dict[DNSQuestion, int] = {
        question: (question.max_size + sum(answer.max_size_compressed for answer in known_answers))
        for question, known_answers in question_with_known_answers.items()
    }
    max_bucket_size = _MAX_MSG_TYPICAL - _DNS_PACKET_HEADER_LEN
    query_buckets: List[_DNSPointerOutgoingBucket] = []
    for question in sorted(
        query_by_size,
        key=query_by_size.get,  # type: ignore
        reverse=True,
    ):
        max_compressed_size = query_by_size[question]
        answers = question_with_known_answers[question]
        for query_bucket in query_buckets:
            if query_bucket.bytes + max_compressed_size <= max_bucket_size:
                query_bucket.add(max_compressed_size, question, answers)
                break
        else:
            # If a single question and known answers won't fit in a packet
            # we will end up generating multiple packets, but there will never
            # be multiple questions
            query_bucket = _DNSPointerOutgoingBucket(now, multicast)
            query_bucket.add(max_compressed_size, question, answers)
            query_buckets.append(query_bucket)

    return [query_bucket.out for query_bucket in query_buckets]


def generate_service_query(
    zc: 'Zeroconf',
    now: float,
    types_: List[str],
    multicast: bool = True,
    question_type: Optional[DNSQuestionType] = None,
) -> List[DNSOutgoing]:
    """Generate a service query for sending with zeroconf.send."""
    questions_with_known_answers: _QuestionWithKnownAnswers = {}
    qu_question = not multicast if question_type is None else question_type == DNSQuestionType.QU
    for type_ in types_:
        question = DNSQuestion(type_, _TYPE_PTR, _CLASS_IN)
        question.unicast = qu_question
        known_answers = {
            record
            for record in zc.cache.get_all_by_details(type_, _TYPE_PTR, _CLASS_IN)
            if not record.is_stale(now)
        }
        if not qu_question and zc.question_history.suppresses(question, now, known_answers):
            log.debug("Asking %s was suppressed by the question history", question)
            continue
        if TYPE_CHECKING:
            pointer_known_answers = cast(Set[DNSPointer], known_answers)
        else:
            pointer_known_answers = known_answers
        questions_with_known_answers[question] = pointer_known_answers
        if not qu_question:
            zc.question_history.add_question_at_time(question, now, known_answers)

    return _group_ptr_queries_with_known_answers(now, multicast, questions_with_known_answers)


def _service_state_changed_from_listener(listener: ServiceListener) -> Callable[..., None]:
    """Generate a service_state_changed handlers from a listener."""
    assert listener is not None
    if not hasattr(listener, 'update_service'):
        warnings.warn(
            "%r has no update_service method. Provide one (it can be empty if you "
            "don't care about the updates), it'll become mandatory." % (listener,),
            FutureWarning,
        )

    def on_change(
        zeroconf: 'Zeroconf', service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        getattr(listener, _ON_CHANGE_DISPATCH[state_change])(zeroconf, service_type, name)

    return on_change


class QueryScheduler:
    """Schedule outgoing PTR queries for Continuous Multicast DNS Querying

    https://datatracker.ietf.org/doc/html/rfc6762#section-5.2

    """

    __slots__ = ('_types', '_next_time', '_first_random_delay_interval', '_delay')

    def __init__(
        self,
        types: Set[str],
        delay: int,
        first_random_delay_interval: Tuple[int, int],
    ) -> None:
        self._types = types
        self._next_time: Dict[str, float] = {}
        self._first_random_delay_interval = first_random_delay_interval
        self._delay: Dict[str, float] = {check_type_: delay for check_type_ in self._types}

    def start(self, now: float_) -> None:
        """Start the scheduler."""
        self._generate_first_next_time(now)

    def _generate_first_next_time(self, now: float_) -> None:
        """Generate the initial next query times.

        https://datatracker.ietf.org/doc/html/rfc6762#section-5.2
        To avoid accidental synchronization when, for some reason, multiple
        clients begin querying at exactly the same moment (e.g., because of
        some common external trigger event), a Multicast DNS querier SHOULD
        also delay the first query of the series by a randomly chosen amount
        in the range 20-120 ms.
        """
        delay = millis_to_seconds(random.randint(*self._first_random_delay_interval))
        next_time = now + delay
        self._next_time = {check_type_: next_time for check_type_ in self._types}

    def millis_to_wait(self, now: float_) -> float:
        """Returns the number of milliseconds to wait for the next event."""
        # Wait for the type has the smallest next time
        next_time = min(self._next_time.values())
        return 0 if next_time <= now else next_time - now

    def reschedule_type(self, type_: str_, next_time: float_) -> bool:
        """Reschedule the query for a type to happen sooner."""
        if next_time >= self._next_time[type_]:
            return False
        self._next_time[type_] = next_time
        return True

    def process_ready_types(self, now: float_) -> List[str]:
        """Generate a list of ready types that is due and schedule the next time."""
        if self.millis_to_wait(now):
            return []

        ready_types: List[str] = []

        for type_, due in self._next_time.items():
            if due > now:
                continue

            ready_types.append(type_)
            self._next_time[type_] = now + self._delay[type_]
            self._delay[type_] = min(_BROWSER_BACKOFF_LIMIT * 1000, self._delay[type_] * 2)

        return ready_types


class _ServiceBrowserBase(RecordUpdateListener):
    """Base class for ServiceBrowser."""

    __slots__ = (
        'types',
        'zc',
        '_loop',
        'addr',
        'port',
        'multicast',
        'question_type',
        '_pending_handlers',
        '_service_state_changed',
        'query_scheduler',
        'done',
        '_first_request',
        '_next_send_timer',
        '_query_sender_task',
    )

    def __init__(
        self,
        zc: 'Zeroconf',
        type_: Union[str, list],
        handlers: Optional[Union[ServiceListener, List[Callable[..., None]]]] = None,
        listener: Optional[ServiceListener] = None,
        addr: Optional[str] = None,
        port: int = _MDNS_PORT,
        delay: int = _BROWSER_TIME,
        question_type: Optional[DNSQuestionType] = None,
    ) -> None:
        """Used to browse for a service for specific type(s).

        Constructor parameters are as follows:

        * `zc`: A Zeroconf instance
        * `type_`: fully qualified service type name
        * `handler`: ServiceListener or Callable that knows how to process ServiceStateChange events
        * `listener`: ServiceListener
        * `addr`: address to send queries (will default to multicast)
        * `port`: port to send queries (will default to mdns 5353)
        * `delay`: The initial delay between answering questions
        * `question_type`: The type of questions to ask (DNSQuestionType.QM or DNSQuestionType.QU)

        The listener object will have its add_service() and
        remove_service() methods called when this browser
        discovers changes in the services availability.
        """
        assert handlers or listener, 'You need to specify at least one handler'
        self.types: Set[str] = set(type_ if isinstance(type_, list) else [type_])
        for check_type_ in self.types:
            # Will generate BadTypeInNameException on a bad name
            service_type_name(check_type_, strict=False)
        self.zc = zc
        assert zc.loop is not None
        self._loop = zc.loop
        self.addr = addr
        self.port = port
        self.multicast = self.addr in (None, _MDNS_ADDR, _MDNS_ADDR6)
        self.question_type = question_type
        self._pending_handlers: Dict[Tuple[str, str], ServiceStateChange] = {}
        self._service_state_changed = Signal()
        self.query_scheduler = QueryScheduler(self.types, delay, _FIRST_QUERY_DELAY_RANDOM_INTERVAL)
        self.done = False
        self._first_request: bool = True
        self._next_send_timer: Optional[asyncio.TimerHandle] = None
        self._query_sender_task: Optional[asyncio.Task] = None

        if hasattr(handlers, 'add_service'):
            listener = cast('ServiceListener', handlers)
            handlers = None

        handlers = cast(List[Callable[..., None]], handlers or [])

        if listener:
            handlers.append(_service_state_changed_from_listener(listener))

        for h in handlers:
            self.service_state_changed.register_handler(h)

    def _async_start(self) -> None:
        """Generate the next time and setup listeners.

        Must be called by uses of this base class after they
        have finished setting their properties.
        """
        self.query_scheduler.start(current_time_millis())
        self.zc.async_add_listener(self, [DNSQuestion(type_, _TYPE_PTR, _CLASS_IN) for type_ in self.types])
        # Only start queries after the listener is installed
        self._query_sender_task = asyncio.ensure_future(self._async_start_query_sender())

    @property
    def service_state_changed(self) -> SignalRegistrationInterface:
        return self._service_state_changed.registration_interface

    def _names_matching_types(self, names: Iterable[str]) -> List[Tuple[str, str]]:
        """Return the type and name for records matching the types we are browsing."""
        return [
            (type_, name) for name in names for type_ in self.types.intersection(cached_possible_types(name))
        ]

    def _enqueue_callback(
        self,
        state_change: ServiceStateChange,
        type_: str_,
        name: str_,
    ) -> None:
        # Code to ensure we only do a single update message
        # Precedence is; Added, Remove, Update
        key = (name, type_)
        if (
            state_change is SERVICE_STATE_CHANGE_ADDED
            or (
                state_change is SERVICE_STATE_CHANGE_REMOVED
                and self._pending_handlers.get(key) != SERVICE_STATE_CHANGE_ADDED
            )
            or (state_change is SERVICE_STATE_CHANGE_UPDATED and key not in self._pending_handlers)
        ):
            self._pending_handlers[key] = state_change

    def async_update_records(self, zc: 'Zeroconf', now: float_, records: List[RecordUpdate]) -> None:
        """Callback invoked by Zeroconf when new information arrives.

        Updates information required by browser in the Zeroconf cache.

        Ensures that there is are no unnecessary duplicates in the list.

        This method will be run in the event loop.
        """
        for record_update in records:
            record, old_record = record_update
            record_type = record.type

            if record_type is _TYPE_PTR:
                if TYPE_CHECKING:
                    record = cast(DNSPointer, record)
                for type_ in self.types.intersection(cached_possible_types(record.name)):
                    if old_record is None:
                        self._enqueue_callback(SERVICE_STATE_CHANGE_ADDED, type_, record.alias)
                    elif record.is_expired(now):
                        self._enqueue_callback(SERVICE_STATE_CHANGE_REMOVED, type_, record.alias)
                    else:
                        expire_time = record.get_expiration_time(_EXPIRE_REFRESH_TIME_PERCENT)
                        self.reschedule_type(type_, now, expire_time)
                continue

            # If its expired or already exists in the cache it cannot be updated.
            if old_record or record.is_expired(now):
                continue

            if record_type in _ADDRESS_RECORD_TYPES:
                cache = self.zc.cache
                # Iterate through the DNSCache and callback any services that use this address
                for type_, name in self._names_matching_types(
                    {service.name for service in cache.async_entries_with_server(record.name)}
                ):
                    self._enqueue_callback(SERVICE_STATE_CHANGE_UPDATED, type_, name)
                continue

            for type_, name in self._names_matching_types((record.name,)):
                self._enqueue_callback(SERVICE_STATE_CHANGE_UPDATED, type_, name)

    def async_update_records_complete(self) -> None:
        """Called when a record update has completed for all handlers.

        At this point the cache will have the new records.

        This method will be run in the event loop.

        This method is expected to be overridden by subclasses.
        """
        for pending in self._pending_handlers.items():
            self._fire_service_state_changed_event(pending)
        self._pending_handlers.clear()

    def _fire_service_state_changed_event(self, event: Tuple[Tuple[str, str], ServiceStateChange]) -> None:
        """Fire a service state changed event.

        When running with ServiceBrowser, this will happen in the dedicated
        thread.

        When running with AsyncServiceBrowser, this will happen in the event loop.
        """
        name_type = event[0]
        state_change = event[1]
        self._service_state_changed.fire(
            zeroconf=self.zc,
            service_type=name_type[1],
            name=name_type[0],
            state_change=state_change,
        )

    def _async_cancel(self) -> None:
        """Cancel the browser."""
        self.done = True
        self._cancel_send_timer()
        self.zc.async_remove_listener(self)
        assert self._query_sender_task is not None, "Attempted to cancel a browser that was not started"
        self._query_sender_task.cancel()

    def _generate_ready_queries(self, first_request: bool_, now: float_) -> List[DNSOutgoing]:
        """Generate the service browser query for any type that is due."""
        ready_types = self.query_scheduler.process_ready_types(now)
        if not ready_types:
            return []

        # If they did not specify and this is the first request, ask QU questions
        # https://datatracker.ietf.org/doc/html/rfc6762#section-5.4 since we are
        # just starting up and we know our cache is likely empty. This ensures
        # the next outgoing will be sent with the known answers list.
        question_type = DNSQuestionType.QU if not self.question_type and first_request else self.question_type
        return generate_service_query(self.zc, now, ready_types, self.multicast, question_type)

    async def _async_start_query_sender(self) -> None:
        """Start scheduling queries."""
        if not self.zc.started:
            await self.zc.async_wait_for_start()
        self._async_send_ready_queries_schedule_next()

    def _cancel_send_timer(self) -> None:
        """Cancel the next send."""
        if self._next_send_timer:
            self._next_send_timer.cancel()
            self._next_send_timer = None

    def reschedule_type(self, type_: str_, now: float_, next_time: float_) -> None:
        """Reschedule a type to be refreshed in the future."""
        if self.query_scheduler.reschedule_type(type_, next_time):
            # We need to send the queries before rescheduling the next one
            # otherwise we may be scheduling a query to go out in the next
            # iteration of the event loop which should be sent now.
            if now >= next_time:
                self._async_send_ready_queries(now)
            self._cancel_send_timer()
            self._async_schedule_next(now)

    def _async_send_ready_queries(self, now: float_) -> None:
        """Send any ready queries."""
        outs = self._generate_ready_queries(self._first_request, now)
        if outs:
            self._first_request = False
            for out in outs:
                self.zc.async_send(out, addr=self.addr, port=self.port)

    def _async_send_ready_queries_schedule_next(self) -> None:
        """Send ready queries and schedule next one checking for done first."""
        if self.done or self.zc.done:
            return
        now = current_time_millis()
        self._async_send_ready_queries(now)
        self._async_schedule_next(now)

    def _async_schedule_next(self, now: float_) -> None:
        """Scheule the next time."""
        delay = millis_to_seconds(self.query_scheduler.millis_to_wait(now))
        self._next_send_timer = self._loop.call_later(delay, self._async_send_ready_queries_schedule_next)


class ServiceBrowser(_ServiceBrowserBase, threading.Thread):
    """Used to browse for a service of a specific type.

    The listener object will have its add_service() and
    remove_service() methods called when this browser
    discovers changes in the services availability."""

    def __init__(
        self,
        zc: 'Zeroconf',
        type_: Union[str, list],
        handlers: Optional[Union[ServiceListener, List[Callable[..., None]]]] = None,
        listener: Optional[ServiceListener] = None,
        addr: Optional[str] = None,
        port: int = _MDNS_PORT,
        delay: int = _BROWSER_TIME,
        question_type: Optional[DNSQuestionType] = None,
    ) -> None:
        assert zc.loop is not None
        if not zc.loop.is_running():
            raise RuntimeError("The event loop is not running")
        threading.Thread.__init__(self)
        super().__init__(zc, type_, handlers, listener, addr, port, delay, question_type)
        # Add the queue before the listener is installed in _setup
        # to ensure that events run in the dedicated thread and do
        # not block the event loop
        self.queue: queue.SimpleQueue = queue.SimpleQueue()
        self.daemon = True
        self.start()
        zc.loop.call_soon_threadsafe(self._async_start)
        self.name = "zeroconf-ServiceBrowser-{}-{}".format(
            '-'.join([type_[:-7] for type_ in self.types]),
            getattr(self, 'native_id', self.ident),
        )

    def cancel(self) -> None:
        """Cancel the browser."""
        assert self.zc.loop is not None
        self.queue.put(None)
        self.zc.loop.call_soon_threadsafe(self._async_cancel)
        self.join()

    def run(self) -> None:
        """Run the browser thread."""
        while True:
            event = self.queue.get()
            if event is None:
                return
            self._fire_service_state_changed_event(event)

    def async_update_records_complete(self) -> None:
        """Called when a record update has completed for all handlers.

        At this point the cache will have the new records.

        This method will be run in the event loop.
        """
        for pending in self._pending_handlers.items():
            self.queue.put(pending)
        self._pending_handlers.clear()

    def __enter__(self) -> 'ServiceBrowser':
        return self

    def __exit__(  # pylint: disable=useless-return
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        self.cancel()
        return None
