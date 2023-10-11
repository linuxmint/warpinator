
import cython

from .._cache cimport DNSCache
from .._dns cimport DNSAddress, DNSPointer, DNSQuestion, DNSRecord, DNSRRSet
from .._history cimport QuestionHistory
from .._protocol.incoming cimport DNSIncoming
from .._services.info cimport ServiceInfo
from .._services.registry cimport ServiceRegistry
from .answers cimport QuestionAnswers


cdef object TYPE_CHECKING
cdef cython.uint _ONE_SECOND, _TYPE_PTR, _TYPE_ANY, _TYPE_A, _TYPE_AAAA, _TYPE_SRV, _TYPE_TXT
cdef str _SERVICE_TYPE_ENUMERATION_NAME
cdef cython.set _RESPOND_IMMEDIATE_TYPES
cdef cython.set _ADDRESS_RECORD_TYPES
cdef object IPVersion
cdef object _TYPE_PTR, _CLASS_IN, _DNS_OTHER_TTL

cdef class _QueryResponse:

    cdef bint _is_probe
    cdef cython.list _questions
    cdef float _now
    cdef DNSCache _cache
    cdef cython.dict _additionals
    cdef cython.set _ucast
    cdef cython.set _mcast_now
    cdef cython.set _mcast_aggregate
    cdef cython.set _mcast_aggregate_last_second

    @cython.locals(record=DNSRecord)
    cdef add_qu_question_response(self, cython.dict answers)

    cdef add_ucast_question_response(self, cython.dict answers)

    @cython.locals(answer=DNSRecord, question=DNSQuestion)
    cdef add_mcast_question_response(self, cython.dict answers)

    @cython.locals(maybe_entry=DNSRecord)
    cdef bint _has_mcast_within_one_quarter_ttl(self, DNSRecord record)

    @cython.locals(maybe_entry=DNSRecord)
    cdef bint _has_mcast_record_in_last_second(self, DNSRecord record)

    cdef QuestionAnswers answers(self)

cdef class QueryHandler:

    cdef ServiceRegistry registry
    cdef DNSCache cache
    cdef QuestionHistory question_history

    @cython.locals(service=ServiceInfo)
    cdef _add_service_type_enumeration_query_answers(self, cython.dict answer_set, DNSRRSet known_answers)

    @cython.locals(service=ServiceInfo)
    cdef _add_pointer_answers(self, str lower_name, cython.dict answer_set, DNSRRSet known_answers)

    @cython.locals(service=ServiceInfo, dns_address=DNSAddress)
    cdef _add_address_answers(self, str lower_name, cython.dict answer_set, DNSRRSet known_answers, object type_)

    @cython.locals(question_lower_name=str, type_=cython.uint, service=ServiceInfo)
    cdef cython.dict _answer_question(self, DNSQuestion question, DNSRRSet known_answers)

    @cython.locals(
        msg=DNSIncoming,
        question=DNSQuestion,
        answer_set=cython.dict,
        known_answers=DNSRRSet,
        known_answers_set=cython.set,
        is_probe=object,
        now=object
    )
    cpdef async_response(self, cython.list msgs, cython.bint unicast_source)
