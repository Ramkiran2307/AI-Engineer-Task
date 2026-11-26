"""Turn parsed messages into compact, LLM-friendly lines.

Every line carries the message id, an absolute date WITH weekday, and the
sender, so the model can resolve "kal", "this Sunday", "Saturday ko" and can
cite messages by id.
"""
from __future__ import annotations

from .parser import Message


def render_message(m: Message) -> str:
    when = m.ts.strftime("%a %d %b %Y %H:%M")
    who = m.sender or "SYSTEM"
    if m.is_media:
        body = "<media omitted: an image/file was shared, its content is NOT available>"
    elif m.is_deleted:
        body = "<message deleted: content NOT available>"
    else:
        body = m.text.replace("\n", "\n    ")  # keep multi-line messages readable
    if m.is_edited:
        body += "  (edited)"
    return f"[#{m.id}|{when}|{who}] {body}"


def render_messages(messages: list[Message]) -> str:
    return "\n".join(render_message(m) for m in messages if not _is_noise(m))


def _is_noise(m: Message) -> bool:
    return m.is_system and "end-to-end encrypted" in m.text.lower()


def chat_header(messages: list[Message]) -> str:
    people = sorted({m.sender for m in messages if m.sender})
    first, last = messages[0].ts, messages[-1].ts
    return (
        f"Participants: {', '.join(people)}\n"
        f"Chat covers {first:%a %d %b %Y} to {last:%a %d %b %Y} ({len(messages)} messages). "
        f"The LAST message is on {last:%a %d %b %Y %H:%M}; nothing after that is known."
    )
