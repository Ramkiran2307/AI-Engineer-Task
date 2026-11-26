"""Prompts and JSON schemas. Nothing here may mention a specific chat's facts."""

PROMPT_VERSION = "v6"

CHAT_RULES = """\
How to read the chat:
- Each line is [#id|Weekday DD Mon YYYY HH:MM|sender] text. Use the weekday/date to resolve relative
  dates ("kal" = the day after (or before) that message, "this Sunday", "Saturday ko", "next week").
- The chat may be in English, Hindi written in Latin script (Hinglish), or a mix. Common words:
  main/mai/mein(=I, when it is the subject) · mera/mere/meri(=my/mine) · tum/tu/aap(=you) · hum(=we) ·
  karunga/kar lunga/kar dunga(=I will do) · kar diya/ho gaya/done(=done) · nahi/nahi ho paya(=not / couldn't) ·
  baad mein(=later) · shayad(=maybe) · pakka(=for sure) · le leta hoon(=I'll take it) · koi nahi(=nobody) ·
  bacha hai/pending(=still remaining) · chahiye(=needed) · mat lo(=don't take/use) · theek hai(=ok).
  In a task list written by someone, "Main - X" means the SENDER takes X.
- LATER MESSAGES OVERRIDE EARLIER ONES. Words like "final" or "decided" do not protect a decision from being
  reversed later. Always look for the most recent message on a topic.
- A promise ("kal tak", "by Sunday", "will do") is NOT completion. Only an explicit "done / merged / ready /
  bought" counts as done. Teammates mocking a promise is a sign it is unreliable.
- A proposal, a question, or one person's opinion is NOT a decision unless someone with the say agrees or
  the group goes along with it. A question like "can X take Y?" becomes a handover only if X accepts.
- Replies are not always the line directly above; match a reply to the message it actually answers.
- <media omitted> and <message deleted> have NO readable content. Never guess what they contained.
- Nothing after the last message is known. Plans for later dates are only plans."""

# --------------------------------------------------------------------------- ledger (map step)
EXTRACT_SYSTEM = f"""\
You extract a structured, time-ordered ledger of project facts from a team group chat.

{CHAT_RULES}

Extract one event for every message (or short exchange) that carries project information: proposals,
decisions, reversals, task assignments, handovers, people dropping a task, status/progress updates,
promises with dates, missed promises, deadlines and date changes, purchases/costs, requirements from
outside (teacher, client, college), meetings, and unresolved questions. Skip greetings and pure jokes.

For each event:
- type: one of proposal | decision | assignment | unassignment | status | commitment | deadline | info | open_question
- topic: a short lowercase name of the workstream/subject (e.g. "backend stack", "login feature", "demo date").
  Reuse EXACTLY the same topic string for every event about the same subject.
- summary: one English sentence. Name people explicitly (resolve I/main/you), give absolute dates
  (e.g. "Sun 15 Nov 2026"), say if it reverses or replaces an earlier event.
- people: names involved.
- certainty: "confirmed" (agreed/done/stated as fact) or "tentative" (proposal, maybe, question, promise, opinion).
- msg_ids: the ids of the message(s) that establish it (integers from the [#id|...] prefix)."""

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["proposal", "decision", "assignment", "unassignment", "status",
                                                        "commitment", "deadline", "info", "open_question"]},
                    "topic": {"type": "string"},
                    "summary": {"type": "string"},
                    "people": {"type": "array", "items": {"type": "string"}},
                    "certainty": {"type": "string", "enum": ["confirmed", "tentative"]},
                    "msg_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["type", "topic", "summary", "people", "certainty", "msg_ids"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["events"],
    "additionalProperties": False,
}

# --------------------------------------------------------------------------- state (reduce step)
STATE_SYSTEM = f"""\
You build the CURRENT "state of the project" from a team chat and a time-ordered ledger of extracted events.
The ledger was produced by an earlier pass and can contain mistakes; when the raw messages are provided,
they are the source of truth.

{CHAT_RULES}

Rules for the state:
- decisions: one entry per topic with the CURRENT decision. If it changed, list the earlier versions in
  `history` (oldest first, each with its date). Use status "tentative" if it was never clearly agreed.
  Only list something as a decision if a message shows the group (or the person in charge) agreeing or
  making the call. If only options were shared or only one person stated a preference, it is NOT a
  decision: put it in open_items ("X not decided yet; Y prefers ...").
- owners: one entry per workstream/task with its CURRENT owner after all handovers, and its latest known
  status: done | in_progress | not_started | blocked | unknown. Put promises and misses in `detail`.
- deadlines: current date of each deadline/event, with how it changed in `history`. certainty "confirmed"
  if stated by an authority or agreed; "derived" if worked out from a rule; "tentative" if uncertain.
- unassigned: work that was dropped or never given to anyone and that nobody has taken as of the last message.
- open_items: other unresolved things: open questions, pending/overdue promises, decisions not yet made,
  planned meetings whose outcome is unknown.
- Every entry MUST cite the msg_ids that support it (the latest ones especially). Do not invent anything."""

_ITEM_IDS = {"type": "array", "items": {"type": "integer"}}
_STR_LIST = {"type": "array", "items": {"type": "string"}}


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


STATE_SCHEMA = _obj({
    "project": {"type": "string"},
    "decisions": {"type": "array", "items": _obj({
        "topic": {"type": "string"}, "current": {"type": "string"},
        "status": {"type": "string", "enum": ["final", "tentative"]},
        "history": _STR_LIST, "msg_ids": _ITEM_IDS})},
    "owners": {"type": "array", "items": _obj({
        "workstream": {"type": "string"}, "owner": {"type": "string"},
        "status": {"type": "string", "enum": ["done", "in_progress", "not_started", "blocked", "unknown"]},
        "detail": {"type": "string"}, "msg_ids": _ITEM_IDS})},
    "deadlines": {"type": "array", "items": _obj({
        "item": {"type": "string"}, "date": {"type": "string"},
        "certainty": {"type": "string", "enum": ["confirmed", "derived", "tentative"]},
        "history": _STR_LIST, "msg_ids": _ITEM_IDS})},
    "unassigned": {"type": "array", "items": _obj({
        "item": {"type": "string"}, "detail": {"type": "string"}, "msg_ids": _ITEM_IDS})},
    "open_items": {"type": "array", "items": _obj({
        "item": {"type": "string"}, "detail": {"type": "string"}, "msg_ids": _ITEM_IDS})},
})

# --------------------------------------------------------------------------- question answering
ANSWER_SYSTEM = f"""\
You answer questions about a team group chat. You are careful: a confident wrong answer is worse than
saying the chat doesn't say.

{CHAT_RULES}

Answering rules:
- Use ONLY the chat messages provided. The ledger/state are hints from an earlier pass and may be wrong;
  check every claim against the messages.
- Give the CURRENT answer as of the last message, and if it changed over time, say briefly what it was before
  and when it changed (fill `changed_over_time`, else "").
- status:
  "answered"    the messages clearly answer the question;
  "partial"     part is answered, part is not in the chat (say which part is unknown);
  "not_in_chat" the chat does not contain the answer. Then say clearly that the chat doesn't say it
                ("The chat doesn't say ..."), and you may add the latest related thing the chat DOES say.
  Do not stretch a related fact into an answer: a single cost is not a total budget, one person's
  preference is not a group decision, a plan or target date is not a status.
- evidence: the messages your answer relies on, most important first, including the LATEST message on the
  topic. For each: msg_id (integer), quote = a short EXACT copy of words from that message (original
  language, no paraphrase), why = what it shows. Do not cite messages that don't support the answer.
- "Is X done / live / finished now?": if the last message on it is only a plan or promise, do NOT claim it
  is or isn't done now; say the chat doesn't confirm it and give the latest known plan with its date.
- Write the answer in the language named in the prompt (it is detected from the question).
- Be concise: 1-4 sentences. Mention names and dates."""

ANSWER_SCHEMA = _obj({
    "status": {"type": "string", "enum": ["answered", "partial", "not_in_chat"]},
    "answer": {"type": "string"},
    "changed_over_time": {"type": "string"},
    "evidence": {"type": "array", "items": _obj({
        "msg_id": {"type": "integer"}, "quote": {"type": "string"}, "why": {"type": "string"}})},
    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
})


REVIEW_SYSTEM = f"""You are a strict reviewer of an answer about a team group chat. A confident wrong answer is worse than
saying the chat doesn't say. You get the chat, the question and a DRAFT answer (JSON).

{CHAT_RULES}

Check the draft claim by claim against the messages:
1. Is each claim directly supported by a message? Remove or correct anything that is not.
2. Is there a LATER message that changes or reverses a claim? Then the later one wins.
3. Does the draft stretch a related fact into an answer (a single cost presented as a total, an opinion
   presented as a decision, a plan/target presented as done or not done, a question presented as a
   handover)? Then change status to "partial" or "not_in_chat" and say what the chat does and doesn't say.
4. Does it say "the chat doesn't say" although a message does answer it? Then answer it.
5. Are the evidence msg_ids and EXACT quotes right, and is the latest relevant message cited?
Return the corrected answer as JSON with the same fields as the draft (return it unchanged if it is right).
Keep the language the prompt asks for."""


# Hindi words that are not also common English words ("the", "me", "par" are left out on purpose).
_HINGLISH_MARKERS = set("""
kya kaun kab kahan kyun kaise kitna kitne kis kisne kiska kiski kiske hai hain tha thi ho hua hui
ne ka ki ke ko se mein pe kar karo karna kiya diya diye raha rahi rahe abhi aur nahi haan koi kuch liye
wala wali wale kaam gaya gayi bata batao chahiye hoga hogi sakta sakti
""".split())


def answer_language(question: str) -> str:
    """Deterministic language pick for the reply: 'Hinglish' or 'English'."""
    import re
    if re.search(r"[ऀ-ॿ]", question):
        return "Hinglish"
    words = re.findall(r"[a-z]+", question.lower())
    hits = sum(w in _HINGLISH_MARKERS for w in words)
    return "Hinglish" if hits >= 2 and hits / max(len(words), 1) >= 0.2 else "English"
