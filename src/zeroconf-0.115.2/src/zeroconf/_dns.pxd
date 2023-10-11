
import cython

from ._protocol.outgoing cimport DNSOutgoing


cdef object _LEN_BYTE
cdef object _LEN_SHORT
cdef object _LEN_INT

cdef object _NAME_COMPRESSION_MIN_SIZE
cdef object _BASE_MAX_SIZE

cdef cython.uint _EXPIRE_FULL_TIME_MS
cdef cython.uint _EXPIRE_STALE_TIME_MS
cdef cython.uint _RECENT_TIME_MS

cdef object _CLASS_UNIQUE
cdef object _CLASS_MASK

cdef object current_time_millis

cdef class DNSEntry:

    cdef public str key
    cdef public str name
    cdef public object type
    cdef public object class_
    cdef public object unique

    cdef _dns_entry_matches(self, DNSEntry other)

cdef class DNSQuestion(DNSEntry):

    cdef public cython.int _hash

cdef class DNSRecord(DNSEntry):

    cdef public cython.float ttl
    cdef public cython.float created

    cdef _suppressed_by_answer(self, DNSRecord answer)

    @cython.locals(
        answers=cython.list,
    )
    cpdef suppressed_by(self, object msg)

    cpdef get_remaining_ttl(self, cython.float now)

    cpdef get_expiration_time(self, cython.uint percent)

    cpdef is_expired(self, cython.float now)

    cpdef is_stale(self, cython.float now)

    cpdef is_recent(self, cython.float now)

    cpdef reset_ttl(self, DNSRecord other)

    cpdef set_created_ttl(self, cython.float now, cython.float ttl)

cdef class DNSAddress(DNSRecord):

    cdef public cython.int _hash
    cdef public object address
    cdef public object scope_id

    cdef _eq(self, DNSAddress other)

    cpdef write(self, DNSOutgoing out)


cdef class DNSHinfo(DNSRecord):

    cdef public cython.int _hash
    cdef public object cpu
    cdef public object os

    cdef _eq(self, DNSHinfo other)

    cpdef write(self, DNSOutgoing out)

cdef class DNSPointer(DNSRecord):

    cdef public cython.int _hash
    cdef public str alias
    cdef public str alias_key

    cdef _eq(self, DNSPointer other)

    cpdef write(self, DNSOutgoing out)

cdef class DNSText(DNSRecord):

    cdef public cython.int _hash
    cdef public object text

    cdef _eq(self, DNSText other)

    cpdef write(self, DNSOutgoing out)

cdef class DNSService(DNSRecord):

    cdef public cython.int _hash
    cdef public object priority
    cdef public object weight
    cdef public object port
    cdef public str server
    cdef public str server_key

    cdef _eq(self, DNSService other)

    cpdef write(self, DNSOutgoing out)

cdef class DNSNsec(DNSRecord):

    cdef public cython.int _hash
    cdef public object next_name
    cdef public cython.list rdtypes

    cdef _eq(self, DNSNsec other)

    cpdef write(self, DNSOutgoing out)

cdef class DNSRRSet:

    cdef cython.list _records
    cdef cython.dict _lookup

    @cython.locals(other=DNSRecord)
    cpdef suppresses(self, DNSRecord record)

    @cython.locals(
        record=DNSRecord,
        record_sets=cython.list,
    )
    cdef cython.dict _get_lookup(self)

    cpdef cython.set lookup_set(self)
