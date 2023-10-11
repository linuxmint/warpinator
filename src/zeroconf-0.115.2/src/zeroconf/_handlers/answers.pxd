
import cython

from .._dns cimport DNSRecord
from .._protocol.outgoing cimport DNSOutgoing


cdef class QuestionAnswers:

    cdef public object ucast
    cdef public object mcast_now
    cdef public object mcast_aggregate
    cdef public object mcast_aggregate_last_second


cdef class AnswerGroup:

    cdef public float send_after
    cdef public float send_before
    cdef public cython.dict answers




cdef object _FLAGS_QR_RESPONSE_AA
cdef object NAME_GETTER

cpdef construct_outgoing_multicast_answers(cython.dict answers)

cpdef construct_outgoing_unicast_answers(
    cython.dict answers, bint ucast_source, cython.list questions, object id_
)

@cython.locals(answer=DNSRecord, additionals=cython.set, additional=DNSRecord)
cdef _add_answers_additionals(DNSOutgoing out, cython.dict answers)
