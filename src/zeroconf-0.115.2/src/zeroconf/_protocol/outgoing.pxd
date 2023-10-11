
import cython

from .._cache cimport DNSCache
from .._dns cimport DNSEntry, DNSPointer, DNSQuestion, DNSRecord
from .incoming cimport DNSIncoming


cdef cython.uint _CLASS_UNIQUE
cdef cython.uint _DNS_PACKET_HEADER_LEN
cdef cython.uint _FLAGS_QR_MASK
cdef cython.uint _FLAGS_QR_QUERY
cdef cython.uint _FLAGS_QR_RESPONSE
cdef cython.uint _FLAGS_TC
cdef cython.uint _MAX_MSG_ABSOLUTE
cdef cython.uint _MAX_MSG_TYPICAL

cdef object TYPE_CHECKING

cdef object PACK_BYTE
cdef object PACK_SHORT
cdef object PACK_LONG

cdef object STATE_INIT
cdef object STATE_FINISHED

cdef object LOGGING_IS_ENABLED_FOR
cdef object LOGGING_DEBUG

cdef cython.tuple BYTE_TABLE

cdef class DNSOutgoing:

    cdef public unsigned int flags
    cdef public bint finished
    cdef public object id
    cdef public bint multicast
    cdef public cython.list packets_data
    cdef public cython.dict names
    cdef public cython.list data
    cdef public unsigned int size
    cdef public bint allow_long
    cdef public object state
    cdef public cython.list questions
    cdef public cython.list answers
    cdef public cython.list authorities
    cdef public cython.list additionals

    cdef _reset_for_next_packet(self)

    cdef _write_byte(self, object value)

    cdef _insert_short_at_start(self, object value)

    cdef _replace_short(self, object index, object value)

    cdef _write_int(self, object value)

    cdef cython.bint _write_question(self, DNSQuestion question)

    @cython.locals(
        d=cython.bytes,
        data_view=cython.list,
        length=cython.uint
    )
    cdef cython.bint _write_record(self, DNSRecord record, object now)

    cdef _write_record_class(self, DNSEntry record)

    @cython.locals(
        start_size_int=object
    )
    cdef cython.bint _check_data_limit_or_rollback(self, cython.uint start_data_length, cython.uint start_size)

    cdef _write_questions_from_offset(self, object questions_offset)

    cdef _write_answers_from_offset(self, object answer_offset)

    cdef _write_records_from_offset(self, cython.list records, object offset)

    cdef _has_more_to_add(self, object questions_offset, object answer_offset, object authority_offset, object additional_offset)

    cdef _write_ttl(self, DNSRecord record, object now)

    @cython.locals(
        labels=cython.list,
        label=cython.str,
        index=cython.uint,
        start_size=cython.uint,
        name_length=cython.uint,
    )
    cpdef write_name(self, cython.str name)

    cpdef write_short(self, object value)

    cpdef write_string(self, cython.bytes value)

    cpdef _write_utf(self, cython.str value)

    @cython.locals(
        questions_offset=object,
        answer_offset=object,
        authority_offset=object,
        additional_offset=object,
        questions_written=object,
        answers_written=object,
        authorities_written=object,
        additionals_written=object,
    )
    cdef _packets(self)

    cpdef add_question_or_all_cache(self, DNSCache cache, object now, str name, object type_, object class_)

    cpdef add_question_or_one_cache(self, DNSCache cache, object now, str name, object type_, object class_)

    cpdef add_question(self, DNSQuestion question)

    cpdef add_answer(self, DNSIncoming inp, DNSRecord record)

    @cython.locals(now_float=cython.float)
    cpdef add_answer_at_time(self, DNSRecord record, object now)

    cpdef add_authorative_answer(self, DNSPointer record)

    cpdef add_additional_answer(self, DNSRecord record)

    cpdef is_query(self)

    cpdef is_response(self)
