
import cython

from .._utils.time cimport current_time_millis, millis_to_seconds
from .answers cimport AnswerGroup, construct_outgoing_multicast_answers


cdef object TYPE_CHECKING
cdef tuple MULTICAST_DELAY_RANDOM_INTERVAL
cdef object RAND_INT

cdef class MulticastOutgoingQueue:

    cdef object zc
    cdef object queue
    cdef cython.uint additional_delay
    cdef cython.uint aggregation_delay

    @cython.locals(last_group=AnswerGroup, random_int=cython.uint, random_delay=float, send_after=float, send_before=float)
    cpdef async_add(self, float now, cython.dict answers)

    @cython.locals(pending=AnswerGroup)
    cdef _remove_answers_from_queue(self, cython.dict answers)

    cpdef async_ready(self)
