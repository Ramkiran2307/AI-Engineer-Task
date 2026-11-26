from datetime import datetime
from pathlib import Path

import pytest

from chatqa.parser import ParseError, detect_date_order, parse_chat_file, parse_chat_text
from chatqa.render import render_message

DATA = Path(__file__).resolve().parent.parent / "data" / "team_chat.txt"


@pytest.fixture(scope="module")
def msgs():
    return parse_chat_file(DATA)


def test_message_count(msgs):
    # 107 lines in the file, 5 of them are continuation lines of the task-split message.
    assert len(msgs) == 102


def test_dates_are_day_first(msgs):
    assert msgs[0].ts == datetime(2026, 10, 3, 21, 14)  # 03/10/26 is 3 Oct, not 10 Mar
    assert msgs[-1].ts == datetime(2026, 11, 12, 20, 13)


def test_multiline_message_kept_together(msgs):
    split = next(m for m in msgs if m.text.startswith("Task split"))
    assert split.sender == "Aarav"
    assert split.line == 17
    for part in ["Rohan - auth", "Priya - listings UI", "Meera - payments", "Kabir - search", "Main - deployment"]:
        assert part in split.text


def test_flags(msgs):
    assert msgs[0].is_system and msgs[0].sender is None
    assert sum(m.is_media for m in msgs) == 4
    deleted = [m for m in msgs if m.is_deleted]
    assert len(deleted) == 1 and deleted[0].sender == "Aarav"
    edited = [m for m in msgs if m.is_edited]
    assert len(edited) == 1 and edited[0].text == "Rs 800 theek hai. 5 log hain, split kar lenge"


def test_render_has_weekday_and_id(msgs):
    m = next(m for m in msgs if "this Sunday" in m.text)
    assert render_message(m).startswith(f"[#{m.id}|Mon 09 Nov 2026 17:40|Rohan]")


def test_ids_unique_and_sequential(msgs):
    assert [m.id for m in msgs] == list(range(1, len(msgs) + 1))


def test_us_month_first_24h():
    text = "10/03/26, 21:14 - Ann: hi\n10/13/26, 08:05 - Bob: later\n"
    ms = parse_chat_text(text)
    assert ms[0].ts == datetime(2026, 10, 3, 21, 14)
    assert ms[1].ts == datetime(2026, 10, 13, 8, 5)


def test_ios_brackets_seconds_and_invisible_chars():
    text = (
        "‎[03/10/26, 9:14:05 PM] Ann: hello there\n"
        "second line\n"
        "[04/10/26, 12:01:00 AM] Bob: ‎image omitted\n"
        "[05/10/26, 12:30:00 PM] Ann: noon: lunch?\n"
    )
    ms = parse_chat_text(text)
    assert len(ms) == 3
    assert ms[0].ts == datetime(2026, 10, 3, 21, 14, 5)
    assert ms[0].text == "hello there\nsecond line"
    assert ms[1].ts.hour == 0 and ms[1].is_media
    assert ms[2].ts.hour == 12 and ms[2].text == "noon: lunch?"


def test_ambiguous_dates_resolved_by_ordering():
    # All parts <= 12. As MM/DD the sequence is Jan 2 -> Jan 3 -> Feb 1 (increasing);
    # as DD/MM it would be 1 Feb -> 1 Mar -> 2 Jan (goes backwards).
    assert detect_date_order(["01/02/26", "01/03/26", "02/01/26"]) == "MDY"
    assert detect_date_order(["02/01/26", "03/01/26", "01/02/26"]) == "DMY"


def test_not_a_chat():
    with pytest.raises(ParseError):
        parse_chat_text("hello\nthis is not a whatsapp export\n")


def test_ios_fixture_chat():
    ms = parse_chat_file(Path(__file__).parent / "fixtures" / "hackathon_chat_ios.txt")
    assert len(ms) == 25
    assert ms[0].ts == datetime(2026, 2, 2, 10, 0, 12)
    roles = ms[5]
    assert roles.sender == "Neha" and "main pitch deck banaungi" in roles.text
    assert ms[14].is_media  # <attached: ...jpg>
