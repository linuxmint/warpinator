
import cython

from .._cache cimport DNSCache
from .._protocol.outgoing cimport DNSOutgoing, DNSPointer, DNSQuestion, DNSRecord
from .._updates cimport RecordUpdateListener
from .._utils.time cimport current_time_millis, millis_to_seconds


cdef object TYPE_CHECKING
cdef object cached_possible_types
cdef cython.uint _EXPIRE_REFRESH_TIME_PERCENT
cdef object SERVICE_STATE_CHANGE_ADDED, SERVICE_STATE_CHANGE_REMOVED, SERVICE_STATE_CHANGE_UPDATED

cdef class _DNSPointerOutgoingBucket:

    cdef public object now
    cdef public DNSOutgoing out
    cdef public cython.uint bytes

    cpdef add(self, cython.uint max_compressed_size, DNSQuestion question, cython.set answers)


@cython.locals(answer=DNSPointer)
cdef _group_ptr_queries_with_known_answers(object now, object multicast, cython.dict question_with_known_answers)

cdef class QueryScheduler:

    cdef cython.set _types
    cdef cython.dict _next_time
    cdef object _first_random_delay_interval
    cdef cython.dict _delay

    cpdef millis_to_wait(self, object now)

    cpdef reschedule_type(self, object type_, object next_time)

    cpdef process_ready_types(self, object now)

cdef class _ServiceBrowserBase(RecordUpdateListener):

    cdef public cython.set types
    cdef public object zc
    cdef object _loop
    cdef public object addr
    cdef public object port
    cdef public object multicast
    cdef public object question_type
    cdef public cython.dict _pending_handlers
    cdef public object _service_state_changed
    cdef public QueryScheduler query_scheduler
    cdef public bint done
    cdef public object _first_request
    cdef public object _next_send_timer
    cdef public object _query_sender_task

    cpdef _generate_ready_queries(self, object first_request, object now)

    cpdef _enqueue_callback(self, object state_change, object type_, object name)

    @cython.locals(record=DNSRecord, cache=DNSCache, service=DNSRecord)
    cpdef async_update_records(self, object zc, cython.float now, cython.list records)

    cpdef _names_matching_types(self, object types)

    cpdef reschedule_type(self, object type_, object now, object next_time)

    cpdef _fire_service_state_changed_event(self, cython.tuple event)

    cpdef _async_send_ready_queries_schedule_next(self)

    cpdef _async_schedule_next(self, object now)

    cpdef _async_send_ready_queries(self, object now)

    cpdef _cancel_send_timer(self)

    cpdef async_update_records_complete(self)
