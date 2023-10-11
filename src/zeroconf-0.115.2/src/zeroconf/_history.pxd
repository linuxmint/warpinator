import cython

from ._dns cimport DNSQuestion


cdef cython.double _DUPLICATE_QUESTION_INTERVAL

cdef class QuestionHistory:

    cdef cython.dict _history

    cpdef add_question_at_time(self, DNSQuestion question, float now, cython.set known_answers)

    @cython.locals(than=cython.double, previous_question=cython.tuple, previous_known_answers=cython.set)
    cpdef suppresses(self, DNSQuestion question, cython.double now, cython.set known_answers)

    @cython.locals(than=cython.double, now_known_answers=cython.tuple)
    cpdef async_expire(self, cython.double now)
