
import cython

from ._handlers.record_manager cimport RecordManager
from ._protocol.incoming cimport DNSIncoming
from ._utils.time cimport current_time_millis, millis_to_seconds


cdef object log
cdef object logging_DEBUG
cdef object TYPE_CHECKING

cdef cython.uint _MAX_MSG_ABSOLUTE
cdef cython.uint _DUPLICATE_PACKET_SUPPRESSION_INTERVAL



cdef class AsyncListener:

    cdef public object zc
    cdef RecordManager _record_manager
    cdef public cython.bytes data
    cdef public cython.float last_time
    cdef public DNSIncoming last_message
    cdef public object transport
    cdef public object sock_description
    cdef public cython.dict _deferred
    cdef public cython.dict _timers

    @cython.locals(now=cython.float, msg=DNSIncoming)
    cpdef datagram_received(self, cython.bytes bytes, cython.tuple addrs)

    cdef _cancel_any_timers_for_addr(self, object addr)
