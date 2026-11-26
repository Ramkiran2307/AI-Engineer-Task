"""Parse WhatsApp chat exports into Message objects.

Handles the common export variants:
  Android : 03/10/26, 9:14 PM - Aarav: text
  24h     : 03/10/2026, 21:14 - Aarav: text
  iOS     : [03/10/26, 9:14:05 PM] Aarav: text
plus multi-line messages, system lines, <Media omitted>, deleted and edited
messages, and the narrow no-break space WhatsApp puts before AM/PM.

The date order (DD/MM vs MM/DD vs YYYY/MM/DD) is detected once for the whole
file, because a single line like 03/10/26 is ambiguous on its own.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Invisible characters WhatsApp sprinkles into exports.
_INVISIBLE = dict.fromkeys(map(ord, "‎‏‪‫‬‭‮﻿"), None)
_SPACES = re.compile(r"[    ]")

_HEADER = re.compile(
    r"""^\[?
        (?P<date>\d{1,4}[./-]\d{1,2}[./-]\d{1,4})
        ,?\s+
        (?P<time>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?)
        (?:\s*(?P<ampm>[AaPp]\.?\s?[Mm]\.?))?
        \]?
        \s*(?:-|–|—)?\s*
        (?P<rest>.*)$""",
    re.VERBOSE,
)
# "Sender: text". Sender names don't contain ':' or '"' (system lines often quote things).
_SENDER = re.compile(r'^(?P<sender>[^:"\n]{1,80}?):\s(?P<text>.*)$', re.DOTALL)

_MEDIA = re.compile(
    r"^(<media omitted>|<attached: .*>|(image|video|audio|sticker|gif|document|contact card) omitted)$",
    re.IGNORECASE,
)
_DELETED = re.compile(r"^(this message was deleted|you deleted this message)\.?$", re.IGNORECASE)
_EDITED = re.compile(r"\s*<this message was edited>\s*$", re.IGNORECASE)
_SYSTEM_HINTS = re.compile(
    r"end-to-end encrypted|created group|added you|^.{1,80} (added|removed|left|joined)\b|changed the (subject|group|icon)",
    re.IGNORECASE,
)


@dataclass
class Message:
    id: int                      # 1-based, stable, used for citations
    line: int                    # 1-based line number in the file where the message starts
    ts: datetime
    sender: str | None           # None for system lines
    text: str
    is_system: bool = False
    is_media: bool = False
    is_deleted: bool = False
    is_edited: bool = False
    raw_lines: list[str] = field(default_factory=list)

    @property
    def stamp(self) -> str:
        """Human-readable timestamp, e.g. 'Mon 09 Nov 2026, 5:40 PM'."""
        return self.ts.strftime("%a %d %b %Y, ") + self.ts.strftime("%I:%M %p").lstrip("0")

    def cite(self) -> str:
        who = self.sender or "system"
        return f"#{self.id} · {self.stamp} · {who} · line {self.line}"


class ParseError(ValueError):
    pass


def _clean(line: str) -> str:
    return _SPACES.sub(" ", line.translate(_INVISIBLE)).rstrip("\r\n")


def _split_date(s: str) -> tuple[int, int, int]:
    a, b, c = (int(x) for x in re.split(r"[./-]", s))
    return a, b, c


def detect_date_order(date_strings: list[str]) -> str:
    """Return 'DMY', 'MDY' or 'YMD' for the whole file."""
    parts = [(_split_date(d), d) for d in date_strings]
    if not parts:
        return "DMY"
    if any(len(re.split(r"[./-]", d)[0]) == 4 for _, d in parts):
        return "YMD"
    first_over_12 = any(p[0] > 12 for p, _ in parts)
    second_over_12 = any(p[1] > 12 for p, _ in parts)
    if first_over_12 and not second_over_12:
        return "DMY"
    if second_over_12 and not first_over_12:
        return "MDY"
    # Fully ambiguous (every day <= 12): pick the order that keeps dates non-decreasing.
    def disorder(order: str) -> int:
        seq = []
        for (a, b, c), _ in parts:
            d, m = (a, b) if order == "DMY" else (b, a)
            seq.append((c, m, d))
        return sum(1 for x, y in zip(seq, seq[1:]) if y < x)
    return "MDY" if disorder("MDY") < disorder("DMY") else "DMY"


def _to_datetime(date_s: str, time_s: str, ampm: str | None, order: str) -> datetime:
    a, b, c = _split_date(date_s)
    if order == "YMD":
        y, m, d = a, b, c
    elif order == "MDY":
        m, d, y = a, b, c
    else:
        d, m, y = a, b, c
    if y < 100:
        y += 2000
    tparts = [int(x) for x in re.split(r"[:.]", time_s)]
    hh, mm = tparts[0], tparts[1]
    ss = tparts[2] if len(tparts) > 2 else 0
    if ampm:
        pm = ampm.lower().startswith("p")
        if hh == 12:
            hh = 0
        if pm:
            hh += 12
    return datetime(y, m, d, hh, mm, ss)


def parse_chat_text(text: str) -> list[Message]:
    lines = text.splitlines()
    # Pass 1: find header lines and collect dates for format detection.
    headers: list[tuple[int, re.Match]] = []
    for i, raw in enumerate(lines):
        m = _HEADER.match(_clean(raw))
        if m:
            headers.append((i, m))
    if not headers:
        raise ParseError("No WhatsApp-style message lines found (expected e.g. '03/10/26, 9:14 PM - Name: text').")
    order = detect_date_order([m.group("date") for _, m in headers])

    # Pass 2: build messages, attaching continuation lines to the previous header.
    header_at = {i: m for i, m in headers}
    messages: list[Message] = []
    current: Message | None = None
    for i, raw in enumerate(lines):
        line = _clean(raw)
        if i in header_at:
            m = header_at[i]
            try:
                ts = _to_datetime(m.group("date"), m.group("time"), m.group("ampm"), order)
            except ValueError:
                ts = None
            if ts is None:  # looked like a header but isn't a valid date: treat as continuation
                if current is not None:
                    current.text += "\n" + line
                    current.raw_lines.append(raw)
                continue
            rest = m.group("rest")
            sm = _SENDER.match(rest)
            if sm and not _SYSTEM_HINTS.search(rest.split(":", 1)[0] + " "):
                current = Message(id=len(messages) + 1, line=i + 1, ts=ts,
                                  sender=sm.group("sender").strip(), text=sm.group("text"), raw_lines=[raw])
            else:
                current = Message(id=len(messages) + 1, line=i + 1, ts=ts, sender=None,
                                  text=rest, is_system=True, raw_lines=[raw])
            messages.append(current)
        elif current is not None:
            current.text += "\n" + line
            current.raw_lines.append(raw)
        # lines before the first header are ignored

    for msg in messages:
        msg.text = msg.text.strip()
        if _EDITED.search(msg.text):
            msg.is_edited = True
            msg.text = _EDITED.sub("", msg.text)
        if _MEDIA.match(msg.text):
            msg.is_media = True
        if _DELETED.match(msg.text):
            msg.is_deleted = True
    return messages


def parse_chat_file(path: str | Path) -> list[Message]:
    p = Path(path)
    if not p.exists():
        raise ParseError(f"Chat file not found: {p}")
    return parse_chat_text(p.read_text(encoding="utf-8", errors="replace"))
