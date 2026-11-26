"""Deterministic checks on what the LLM claims. No LLM calls here.

The model cites messages as {msg_id, quote}. We only trust a citation if it can be
matched to a real parsed message:
  - id exists and the quote is (nearly) in that message           -> ok
  - the quote is in a *different* message (model got the id wrong) -> re-pointed to that message
  - id exists but the quote isn't found anywhere                   -> kept, flagged "quote_mismatch"
  - id doesn't exist and quote isn't found                         -> dropped
An answer that claims to be answered but has no surviving evidence is downgraded
to "the chat doesn't say". Printed citations always come from the parsed file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .parser import Message

_WORD = re.compile(r"[\w']+", re.UNICODE)


def _norm(s: str) -> str:
    return " ".join(_WORD.findall(s.lower()))


def quote_matches(quote: str, text: str, threshold: float = 0.75) -> bool:
    q, t = _norm(quote), _norm(text)
    if not q:
        return False
    if q in t:
        return True
    q_words = q.split()
    t_words = set(t.split())
    if len(q_words) < 2:
        return False
    return sum(w in t_words for w in q_words) / len(q_words) >= threshold


@dataclass
class Evidence:
    msg: Message
    quote: str
    why: str
    flag: str = "ok"        # ok | repointed | quote_mismatch


@dataclass
class VerifiedAnswer:
    question: str
    status: str             # answered | partial | not_in_chat
    answer: str
    changed_over_time: str
    confidence: str
    evidence: list[Evidence] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)
    downgraded: bool = False
    raw: dict | None = None
    draft: dict | None = None   # pre-review answer, when the review pass ran

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "status": self.status,
            "answer": self.answer,
            "changed_over_time": self.changed_over_time,
            "confidence": self.confidence,
            "downgraded": self.downgraded,
            "evidence": [
                {"msg_id": e.msg.id, "line": e.msg.line, "timestamp": e.msg.ts.isoformat(timespec="minutes"),
                 "sender": e.msg.sender, "text": e.msg.text, "quote": e.quote, "why": e.why, "flag": e.flag}
                for e in self.evidence
            ],
            "dropped_citations": self.dropped,
            "draft_before_review": self.draft,
        }


def resolve_citation(msg_id, quote: str, by_id: dict[int, Message], messages: list[Message]):
    """Return (Message, flag) or (None, reason)."""
    try:
        msg_id = int(msg_id)
    except (TypeError, ValueError):
        msg_id = None
    msg = by_id.get(msg_id) if msg_id is not None else None
    if msg is not None and (not quote or quote_matches(quote, msg.text)):
        return msg, "ok"
    if quote:
        hits = [m for m in messages if quote_matches(quote, m.text)]
        if hits:
            # prefer the hit closest to the cited id (models are usually off by a few)
            best = min(hits, key=lambda m: abs(m.id - msg_id) if msg_id is not None else 0)
            return best, "repointed"
    if msg is not None:
        return msg, "quote_mismatch"
    return None, "unknown message id and quote not found in chat"


def verify_answer(question: str, raw: dict, messages: list[Message]) -> VerifiedAnswer:
    by_id = {m.id: m for m in messages}
    status = raw.get("status", "not_in_chat")
    if status not in ("answered", "partial", "not_in_chat"):
        status = "not_in_chat"
    out = VerifiedAnswer(
        question=question, status=status, answer=str(raw.get("answer", "")).strip(),
        changed_over_time=str(raw.get("changed_over_time", "") or "").strip(),
        confidence=raw.get("confidence", "low"), raw=raw,
    )
    seen = set()
    for ev in raw.get("evidence", []) or []:
        if not isinstance(ev, dict):
            continue
        quote = str(ev.get("quote", "") or "")
        mid = ev.get("msg_id", ev.get("msg_ids", ev.get("id")))  # tolerate key drift from weaker models
        if isinstance(mid, list):
            mid = mid[0] if mid else None
        msg, flag = resolve_citation(mid, quote, by_id, messages)
        if msg is None:
            out.dropped.append({"msg_id": ev.get("msg_id"), "quote": quote, "reason": flag})
            continue
        if msg.id in seen:
            continue
        seen.add(msg.id)
        out.evidence.append(Evidence(msg=msg, quote=quote, why=str(ev.get("why", "") or ""), flag=flag))

    solid = [e for e in out.evidence if e.flag in ("ok", "repointed")]
    if out.status in ("answered", "partial") and not solid:
        out.downgraded = True
        out.status = "not_in_chat"
        out.confidence = "low"
        # The unverified text stays in `raw` for debugging but is not shown as an answer.
        out.answer = ("The chat doesn't say. (A draft answer was withheld because none of the "
                      "messages it cited could be found in the chat.)")
    return out


def clean_ids(ids, by_id: dict[int, Message]) -> list[int]:
    """Keep only message ids that exist, de-duplicated, in order."""
    out = []
    for i in ids or []:
        try:
            i = int(i)
        except (TypeError, ValueError):
            continue
        if i in by_id and i not in out:
            out.append(i)
    return out
