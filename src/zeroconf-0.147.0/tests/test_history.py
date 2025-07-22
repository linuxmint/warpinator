"""Unit tests for _history.py."""

from __future__ import annotations

import zeroconf as r
from zeroconf import const
from zeroconf._history import QuestionHistory


def test_question_suppression():
    history = QuestionHistory()

    question = r.DNSQuestion("_hap._tcp._local.", const._TYPE_PTR, const._CLASS_IN)
    now = r.current_time_millis()
    other_known_answers: set[r.DNSRecord] = {
        r.DNSPointer(
            "_hap._tcp.local.",
            const._TYPE_PTR,
            const._CLASS_IN,
            10000,
            "known-to-other._hap._tcp.local.",
        )
    }
    our_known_answers: set[r.DNSRecord] = {
        r.DNSPointer(
            "_hap._tcp.local.",
            const._TYPE_PTR,
            const._CLASS_IN,
            10000,
            "known-to-us._hap._tcp.local.",
        )
    }

    history.add_question_at_time(question, now, other_known_answers)

    # Verify the question is suppressed if the known answers are the same
    assert history.suppresses(question, now, other_known_answers)

    # Verify the question is suppressed if we know the answer to all the known answers
    assert history.suppresses(question, now, other_known_answers | our_known_answers)

    # Verify the question is not suppressed if our known answers do no include the ones in the last question
    assert not history.suppresses(question, now, set())

    # Verify the question is not suppressed if our known answers do no include the ones in the last question
    assert not history.suppresses(question, now, our_known_answers)

    # Verify the question is no longer suppressed after 1s
    assert not history.suppresses(question, now + 1000, other_known_answers)


def test_question_expire():
    history = QuestionHistory()

    now = r.current_time_millis()
    question = r.DNSQuestion("_hap._tcp._local.", const._TYPE_PTR, const._CLASS_IN)
    other_known_answers: set[r.DNSRecord] = {
        r.DNSPointer(
            "_hap._tcp.local.",
            const._TYPE_PTR,
            const._CLASS_IN,
            10000,
            "known-to-other._hap._tcp.local.",
            created=now,
        )
    }
    history.add_question_at_time(question, now, other_known_answers)

    # Verify the question is suppressed if the known answers are the same
    assert history.suppresses(question, now, other_known_answers)

    history.async_expire(now)

    # Verify the question is suppressed if the known answers are the same since the cache hasn't expired
    assert history.suppresses(question, now, other_known_answers)

    history.async_expire(now + 1000)

    # Verify the question not longer suppressed since the cache has expired
    assert not history.suppresses(question, now, other_known_answers)
