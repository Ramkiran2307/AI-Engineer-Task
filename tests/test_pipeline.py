"""Pipeline tests with a fake LLM (no network)."""
from pathlib import Path

from chatqa import prompts
from chatqa.llm import LLMConfig, extract_json
from chatqa.parser import parse_chat_file, parse_chat_text
from chatqa.pipeline import ChatQA
from chatqa.report import format_answer, format_state

DATA = Path(__file__).resolve().parent.parent / "data" / "team_chat.txt"


class FakeLLM:
    def __init__(self, responses):
        self.cfg = LLMConfig("fake", "fake-model", None, None)
        self.responses = responses  # system prompt -> dict
        self.contexts = []

    def complete_json(self, system, context, prompt, schema, max_tokens=4000):
        self.contexts.append(context)
        return self.responses[system]


def _fake(msgs):
    pay = next(m.id for m in msgs if "Razorpay test mode final" in m.text)
    return FakeLLM({
        prompts.EXTRACT_SYSTEM: {"events": [
            {"type": "decision", "topic": "payments", "summary": "Back to Razorpay test mode", "people": ["Aarav"],
             "certainty": "confirmed", "msg_ids": [pay]},
            {"type": "info", "topic": "ghost", "summary": "invented", "people": [], "certainty": "confirmed",
             "msg_ids": [5000]},
        ]},
        prompts.STATE_SYSTEM: {"project": "p", "decisions": [
            {"topic": "payments", "current": "Razorpay test mode", "status": "final", "history": [], "msg_ids": [pay, 4242]}],
            "owners": [], "deadlines": [], "unassigned": [], "open_items": []},
        prompts.ANSWER_SYSTEM: {"status": "answered", "answer": "Razorpay test mode.", "changed_over_time": "",
                                "confidence": "high",
                                "evidence": [{"msg_id": pay, "quote": "Razorpay test mode final", "why": "latest"}]},
    }), pay


def test_end_to_end_with_fake_llm(tmp_path):
    msgs = parse_chat_file(DATA)
    llm, pay = _fake(msgs)
    qa = ChatQA(msgs, llm, cache_dir=tmp_path)
    ans = qa.ask("What payment method?")
    assert ans.status == "answered" and ans.evidence[0].msg.id == pay
    # events with non-existent message ids are discarded
    assert [e["topic"] for e in qa.events()] == ["payments"]
    # state citations are sanitised
    assert qa.state()["decisions"][0]["msg_ids"] == [pay]
    # small chat -> whole chat in context
    assert "CHAT MESSAGES (all of them)" in llm.contexts[-1]
    out = format_answer(ans)
    assert f"#{pay}" in out and "Aarav" in out and "line" in out
    assert "Razorpay test mode" in format_state(qa.state(), msgs)


def test_cache_reused(tmp_path):
    msgs = parse_chat_file(DATA)
    llm, _ = _fake(msgs)
    ChatQA(msgs, llm, cache_dir=tmp_path).state()
    n = len(llm.contexts)
    ChatQA(msgs, llm, cache_dir=tmp_path).state()
    assert len(llm.contexts) == n  # second run hit the cache


def test_large_chat_uses_retrieval_and_chunks(tmp_path, monkeypatch):
    import chatqa.pipeline as pl
    monkeypatch.setattr(pl, "FULL_CONTEXT_CHARS", 2000)
    monkeypatch.setattr(pl, "EXTRACT_CHUNK_CHARS", 1500)
    msgs = parse_chat_file(DATA)
    llm, pay = _fake(msgs)
    qa = ChatQA(msgs, llm, cache_dir=tmp_path)
    assert not qa.is_small
    assert len(qa._chunks()) > 3
    ctx = qa.build_context("Razorpay payments final decision")
    assert "most relevant" in ctx
    assert f"[#{pay}|" in ctx  # the reversal message is retrieved


def test_extract_json_tolerates_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope that helps') == {"a": 2}


def test_generic_chat_other_names(tmp_path):
    text = ("12/01/25, 10:00 - Zed: I'll do the poster\n"
            "13/01/25, 11:00 - Yan: ok\n")
    msgs = parse_chat_text(text)
    llm = FakeLLM({prompts.ANSWER_SYSTEM: {"status": "answered", "answer": "Zed", "changed_over_time": "",
                                           "confidence": "high",
                                           "evidence": [{"msg_id": 1, "quote": "I'll do the poster", "why": ""}]}})
    qa = ChatQA(msgs, llm, cache_dir=tmp_path, use_ledger=False)
    assert qa.ask("who does the poster").evidence[0].msg.sender == "Zed"
