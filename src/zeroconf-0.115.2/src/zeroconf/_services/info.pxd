
import cython

from .._cache cimport DNSCache
from .._dns cimport DNSAddress, DNSNsec, DNSPointer, DNSRecord, DNSService, DNSText
from .._protocol.outgoing cimport DNSOutgoing
from .._updates cimport RecordUpdateListener
from .._utils.time cimport current_time_millis


cdef object _resolve_all_futures_to_none
cdef object _cached_ip_addresses_wrapper

cdef object _TYPE_SRV
cdef object _TYPE_TXT
cdef object _TYPE_A
cdef object _TYPE_AAAA
cdef object _TYPE_PTR
cdef object _TYPE_NSEC
cdef object _CLASS_IN
cdef object _FLAGS_QR_QUERY

cdef object service_type_name

cdef object DNS_QUESTION_TYPE_QU
cdef object DNS_QUESTION_TYPE_QM

cdef object _IPVersion_All_value
cdef object _IPVersion_V4Only_value

cdef cython.set _ADDRESS_RECORD_TYPES

cdef object TYPE_CHECKING

cdef class ServiceInfo(RecordUpdateListener):

    cdef public cython.bytes text
    cdef public str type
    cdef str _name
    cdef public str key
    cdef public cython.list _ipv4_addresses
    cdef public cython.list _ipv6_addresses
    cdef public object port
    cdef public object weight
    cdef public object priority
    cdef public str server
    cdef public str server_key
    cdef public cython.dict _properties
    cdef public object host_ttl
    cdef public object other_ttl
    cdef public object interface_index
    cdef public cython.set _new_records_futures
    cdef public DNSPointer _dns_pointer_cache
    cdef public DNSService _dns_service_cache
    cdef public DNSText _dns_text_cache
    cdef public cython.list _dns_address_cache
    cdef public cython.set _get_address_and_nsec_records_cache

    @cython.locals(cache=DNSCache)
    cpdef async_update_records(self, object zc, cython.float now, cython.list records)

    @cython.locals(cache=DNSCache)
    cpdef _load_from_cache(self, object zc, cython.float now)

    cdef _unpack_text_into_properties(self)

    cdef _set_properties(self, cython.dict properties)

    cdef _set_text(self, cython.bytes text)

    @cython.locals(record=DNSAddress)
    cdef _get_ip_addresses_from_cache_lifo(self, object zc, cython.float now, object type)

    @cython.locals(
        dns_service_record=DNSService,
        dns_text_record=DNSText,
        dns_address_record=DNSAddress
    )
    cdef _process_record_threadsafe(self, object zc, DNSRecord record, cython.float now)

    @cython.locals(cache=DNSCache)
    cdef cython.list _get_address_records_from_cache_by_type(self, object zc, object _type)

    cdef _set_ipv4_addresses_from_cache(self, object zc, object now)

    cdef _set_ipv6_addresses_from_cache(self, object zc, object now)

    cdef cython.list _ip_addresses_by_version_value(self, object version_value)

    cpdef addresses_by_version(self, object version)

    cpdef ip_addresses_by_version(self, object version)

    @cython.locals(cacheable=cython.bint)
    cdef cython.list _dns_addresses(self, object override_ttls, object version)

    @cython.locals(cacheable=cython.bint)
    cdef DNSPointer _dns_pointer(self, object override_ttl)

    @cython.locals(cacheable=cython.bint)
    cdef DNSService _dns_service(self, object override_ttl)

    @cython.locals(cacheable=cython.bint)
    cdef DNSText _dns_text(self, object override_ttl)

    cdef DNSNsec _dns_nsec(self, cython.list missing_types, object override_ttl)

    @cython.locals(cacheable=cython.bint)
    cdef cython.set _get_address_and_nsec_records(self, object override_ttl)

    cpdef async_clear_cache(self)
