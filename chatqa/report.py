"""Human-readable output: answers and the state-of-the-project report.

Every citation is printed from the parsed chat file (id, timestamp, sender, line
number, original text) - never from model output.
"""
from __future__ import annotations

import textwrap

from .parser import Message
from .verify import VerifiedAnswer

STATUS_LABEL = {"answered": "ANSWERED", "partial": "PARTIAL (some of it isn't in the chat)",
                "not_in_chat": "NOT IN CHAT"}


_NO_HISTORY = {"", "-", "n/a", "na", "none", "not applicable", "no change", "no changes", "unchanged"}


def _short(text: str, n: int = 160) -> str:
    one = " / ".join(x.strip() for x in text.splitlines() if x.strip())
    return one if len(one) <= n else one[: n - 1] + "…"


def format_answer(a: VerifiedAnswer) -> str:
    out = [f"Q: {a.question}",
           f"Status: {STATUS_LABEL.get(a.status, a.status)}   (confidence: {a.confidence})"]
    out.append("A: " + textwrap.fill(a.answer, 100, subsequent_indent="   "))
    if a.changed_over_time and a.changed_over_time.strip().lower().rstrip(".") not in _NO_HISTORY:
        out.append("History: " + textwrap.fill(a.changed_over_time, 100, subsequent_indent="         "))
    if a.evidence:
        out.append("Evidence (from the chat file):")
        for e in a.evidence:
            m = e.msg
            flag = "" if e.flag == "ok" else f"   [{'id corrected' if e.flag == 'repointed' else 'quote not verbatim'}]"
            out.append(f"  [#{m.id} | {m.stamp} | {m.sender or 'system'} | line {m.line}]{flag}")
            out.append(f"      \"{_short(m.text)}\"")
            if e.why:
                out.append(f"      -> {e.why}")
    elif a.status != "not_in_chat":
        out.append("Evidence: none")
    if a.dropped:
        out.append(f"({len(a.dropped)} citation(s) dropped because they don't match any message)")
    return "\n".join(out)


def _cites(ids: list[int], by_id: dict[int, Message]) -> str:
    if not ids:
        return " ⚠ *no verifiable source*"
    parts = []
    ids = sorted(ids, reverse=True)  # newest first: the latest message is what proves the current state
    for i in ids[:4]:
        m = by_id[i]
        parts.append(f"#{m.id} {m.ts:%d %b} {m.sender or 'system'}")
    more = f" +{len(ids) - 4} earlier" if len(ids) > 4 else ""
    return f" — _[{'; '.join(parts)}{more}]_"


def format_state(state: dict, messages: list[Message], title: str = "State of the project") -> str:
    by_id = {m.id: m for m in messages}
    L = [f"# {title}", ""]
    if state.get("project"):
        L += [f"**Project:** {state['project']}  ", ""]
    L += [f"_As of the last message: {state.get('as_of', '?')}. Nothing after that is known._", ""]

    L += ["## Current decisions", ""]
    for d in state.get("decisions", []):
        tag = "" if d.get("status") == "final" else " *(tentative)*"
        L.append(f"- **{d['topic']}:** {d['current']}{tag}{_cites(d.get('msg_ids', []), by_id)}")
        for h in d.get("history", []) or []:
            L.append(f"    - earlier: {h}")
    if not state.get("decisions"):
        L.append("- (none found)")

    L += ["", "## Who owns what", "", "| Workstream | Owner | Status | Detail | Source |", "|---|---|---|---|---|"]
    for o in state.get("owners", []):
        detail = o.get("detail", "").replace("|", "/")
        L.append(f"| {o['workstream']} | {o['owner']} | {o['status'].replace('_', ' ')} | {detail} |"
                 f"{_cites(o.get('msg_ids', []), by_id).replace(' — ', ' ')} |")

    L += ["", "## Deadlines & dates", ""]
    for d in state.get("deadlines", []):
        L.append(f"- **{d['item']}:** {d['date']} *({d.get('certainty', '?')})*{_cites(d.get('msg_ids', []), by_id)}")
        for h in d.get("history", []) or []:
            L.append(f"    - earlier: {h}")
    if not state.get("deadlines"):
        L.append("- (none found)")

    L += ["", "## Unassigned (nobody is working on it)", ""]
    for u in state.get("unassigned", []):
        L.append(f"- **{u['item']}:** {u['detail']}{_cites(u.get('msg_ids', []), by_id)}")
    if not state.get("unassigned"):
        L.append("- (nothing found)")

    L += ["", "## Still open / unresolved", ""]
    for u in state.get("open_items", []):
        L.append(f"- **{u['item']}:** {u['detail']}{_cites(u.get('msg_ids', []), by_id)}")
    if not state.get("open_items"):
        L.append("- (nothing found)")
    L.append("")
    return "\n".join(L)
