from pathlib import Path

import pytest

from chatqa.parser import parse_chat_file
from chatqa.verify import clean_ids, quote_matches, verify_answer

DATA = Path(__file__).resolve().parent.parent / "data" / "team_chat.txt"


@pytest.fixture(scope="module")
def msgs():
    return parse_chat_file(DATA)


def _id_of(msgs, needle):
    return next(m.id for m in msgs if needle in m.text)


def test_quote_matching():
    assert quote_matches("Razorpay test mode final", "haan. Razorpay test mode final. QR wala scrap.")
    assert quote_matches("razorpay TEST mode, final!", "haan. Razorpay test mode final. QR wala scrap.")
    assert not quote_matches("UPI QR manual", "haan. Razorpay test mode final. QR wala scrap.")
    assert not quote_matches("", "anything")


def test_valid_citation_kept(msgs):
    mid = _id_of(msgs, "Razorpay test mode final")
    a = verify_answer("q", {"status": "answered", "answer": "Razorpay test mode",
                            "evidence": [{"msg_id": mid, "quote": "Razorpay test mode final", "why": ""}]}, msgs)
    assert a.status == "answered" and not a.downgraded
    assert a.evidence[0].msg.id == mid and a.evidence[0].flag == "ok"


def test_wrong_id_is_repointed_by_quote(msgs):
    mid = _id_of(msgs, "Razorpay test mode final")
    a = verify_answer("q", {"status": "answered", "answer": "x",
                            "evidence": [{"msg_id": mid + 3, "quote": "Razorpay test mode final", "why": ""}]}, msgs)
    assert a.evidence[0].msg.id == mid and a.evidence[0].flag == "repointed"


def test_invented_citation_dropped_and_answer_downgraded(msgs):
    a = verify_answer("Who designed the logo?", {
        "status": "answered", "answer": "Priya designed the final logo, it was approved on 13 Nov.",
        "confidence": "high",
        "evidence": [{"msg_id": 9999, "quote": "final logo approved by everyone", "why": ""}]}, msgs)
    assert a.downgraded
    assert a.status == "not_in_chat"
    assert a.answer.startswith("The chat doesn't say")
    assert "Priya designed" not in a.answer  # the unverified guess is not shown
    assert len(a.dropped) == 1 and not a.evidence


def test_quote_mismatch_alone_does_not_count_as_evidence(msgs):
    mid = _id_of(msgs, "Razorpay test mode final")
    a = verify_answer("q", {"status": "answered", "answer": "x",
                            "evidence": [{"msg_id": mid, "quote": "completely different words here", "why": ""}]}, msgs)
    assert a.evidence[0].flag == "quote_mismatch"
    assert a.downgraded and a.status == "not_in_chat"


def test_not_in_chat_is_left_alone(msgs):
    a = verify_answer("q", {"status": "not_in_chat", "answer": "The chat doesn't say.", "evidence": []}, msgs)
    assert a.status == "not_in_chat" and not a.downgraded


def test_bad_status_and_ids_sanitised(msgs):
    a = verify_answer("q", {"status": "definitely", "answer": "x", "evidence": [{"msg_id": "abc", "quote": ""}]}, msgs)
    assert a.status == "not_in_chat"
    assert clean_ids([1, "2", 2, 99999, None, "x"], {m.id: m for m in msgs}) == [1, 2]


def test_key_drift_tolerated_but_invented_quote_still_rejected(msgs):
    # Seen live: model used "msg_ids" and invented the quote "Main nahi kar paunga, koi aur dekh lo".
    a = verify_answer("q", {"status": "answered", "answer": "search unassigned",
                            "evidence": [{"msg_ids": 44, "quote": "Main nahi kar paunga, koi aur dekh lo"}]}, msgs)
    assert a.evidence and a.evidence[0].msg.id == 44 and a.evidence[0].flag == "quote_mismatch"
    assert a.downgraded
    b = verify_answer("q", {"status": "answered", "answer": "search unassigned",
                            "evidence": [{"msg_ids": [44], "quote": "search koi aur le lo please"}]}, msgs)
    assert not b.downgraded and b.evidence[0].flag == "ok"
