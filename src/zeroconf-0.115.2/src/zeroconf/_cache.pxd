import cython

from ._dns cimport (
    DNSAddress,
    DNSEntry,
    DNSHinfo,
    DNSNsec,
    DNSPointer,
    DNSRecord,
    DNSService,
    DNSText,
)


cdef object _UNIQUE_RECORD_TYPES
cdef object _TYPE_PTR
cdef cython.uint _ONE_SECOND

cdef _remove_key(cython.dict cache, object key, DNSRecord record)


cdef class DNSCache:

    cdef public cython.dict cache
    cdef public cython.dict service_cache

    cpdef async_add_records(self, object entries)

    cpdef async_remove_records(self, object entries)

    @cython.locals(
        store=cython.dict,
    )
    cpdef async_get_unique(self, DNSRecord entry)

    @cython.locals(
        record=DNSRecord,
    )
    cpdef async_expire(self, float now)

    @cython.locals(
        records=cython.dict,
        record=DNSRecord,
    )
    cpdef async_all_by_details(self, str name, object type_, object class_)

    cpdef async_entries_with_name(self, str name)

    cpdef async_entries_with_server(self, str name)

    @cython.locals(
        cached_entry=DNSRecord,
    )
    cpdef get_by_details(self, str name, object type_, object class_)

    @cython.locals(
        records=cython.dict,
        entry=DNSRecord,
    )
    cpdef get_all_by_details(self, str name, object type_, object class_)

    @cython.locals(
        store=cython.dict,
    )
    cdef _async_add(self, DNSRecord record)

    cdef _async_remove(self, DNSRecord record)

    @cython.locals(
        record=DNSRecord,
        created_float=cython.float,
    )
    cpdef async_mark_unique_records_older_than_1s_to_expire(self, cython.set unique_types, object answers, float now)
