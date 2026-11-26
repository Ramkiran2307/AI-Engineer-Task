"""The end-to-end pipeline: messages -> ledger -> state, and question -> verified answer."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from . import prompts
from .llm import LLM
from .parser import Message
from .render import chat_header, render_message, render_messages
from .retrieval import BM25
from .verify import VerifiedAnswer, clean_ids, verify_answer

# A chat whose rendered text fits in this many characters is sent to the model whole
# (~15k tokens). Bigger chats use chunked extraction + retrieval.
FULL_CONTEXT_CHARS = int(os.getenv("FULL_CONTEXT_CHARS", "60000"))
EXTRACT_CHUNK_CHARS = int(os.getenv("EXTRACT_CHUNK_CHARS", "20000"))
CHUNK_OVERLAP_MSGS = 6


class ChatQA:
    def __init__(self, messages: list[Message], llm: LLM | None, cache_dir: str | Path = ".cache",
                 use_ledger: bool = True, use_cache: bool = True, verbose: bool = False):
        self.messages = messages
        self.by_id = {m.id: m for m in messages}
        self.llm = llm
        self.use_ledger = use_ledger
        self.use_cache = use_cache
        self.verbose = verbose
        self.header = chat_header(messages)
        self.rendered = render_messages(messages)
        self.is_small = len(self.rendered) <= FULL_CONTEXT_CHARS
        chat_hash = hashlib.sha256(self.rendered.encode("utf-8")).hexdigest()[:16]
        model = llm.cfg.label().replace(":", "_").replace("/", "_") if llm else "none"
        self.cache_dir = Path(cache_dir) / f"{chat_hash}_{model}_{prompts.PROMPT_VERSION}"
        self._events: list[dict] | None = None
        self._state: dict | None = None
        self._bm25_msgs: BM25 | None = None

    # ------------------------------------------------------------------ helpers
    def _log(self, msg: str):
        if self.verbose:
            print(f"[chatqa] {msg}", file=sys.stderr)

    def _cache_get(self, name: str):
        p = self.cache_dir / name
        if self.use_cache and p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def _cache_put(self, name: str, data):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _require_llm(self):
        if self.llm is None:
            raise RuntimeError("No LLM configured. Set an API key in .env (see .env.example) or use --offline.")

    # ------------------------------------------------------------------ ledger (map)
    def _chunks(self) -> list[list[Message]]:
        msgs = [m for m in self.messages if not (m.is_system and "encrypted" in m.text)]
        chunks, cur, size = [], [], 0
        for m in msgs:
            line = len(render_message(m)) + 1
            if cur and size + line > EXTRACT_CHUNK_CHARS:
                chunks.append(cur)
                cur = cur[-CHUNK_OVERLAP_MSGS:]
                size = sum(len(render_message(x)) + 1 for x in cur)
            cur.append(m)
            size += line
        if cur:
            chunks.append(cur)
        return chunks

    def events(self) -> list[dict]:
        if self._events is not None:
            return self._events
        cached = self._cache_get("events.json")
        if cached is not None:
            self._events = cached
            return cached
        self._require_llm()
        chunks = self._chunks()
        raw_events: list[dict] = []
        for n, chunk in enumerate(chunks, 1):
            self._log(f"extracting ledger, chunk {n}/{len(chunks)} (#{chunk[0].id}-#{chunk[-1].id})")
            context = (f"{self.header}\n\nMESSAGES #{chunk[0].id} to #{chunk[-1].id}"
                       f"{' (the first few overlap with the previous chunk)' if n > 1 else ''}:\n"
                       + "\n".join(render_message(m) for m in chunk))
            data = self.llm.complete_json(prompts.EXTRACT_SYSTEM, context,
                                          "Extract the ledger of events for these messages as JSON.",
                                          prompts.EXTRACT_SCHEMA, max_tokens=8000)
            raw_events.extend(data.get("events", []))
        self._events = self._clean_events(raw_events)
        self._cache_put("events.json", self._events)
        return self._events

    def _clean_events(self, raw: list[dict]) -> list[dict]:
        out, seen = [], set()
        for e in raw:
            ids = clean_ids(e.get("msg_ids"), self.by_id)
            if not ids:
                continue  # an event we can't tie to a real message is not kept
            key = (e.get("type"), tuple(ids))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "type": e.get("type", "info"), "topic": str(e.get("topic", "")).strip().lower(),
                "summary": str(e.get("summary", "")).strip(), "people": e.get("people", []) or [],
                "certainty": e.get("certainty", "tentative"), "msg_ids": ids,
            })
        out.sort(key=lambda e: (max(e["msg_ids"]), min(e["msg_ids"])))
        for i, e in enumerate(out, 1):
            e["id"] = f"e{i}"
            e["date"] = self.by_id[max(e["msg_ids"])].ts.strftime("%a %d %b %Y %H:%M")
        return out

    def ledger_text(self, events: list[dict] | None = None) -> str:
        events = self.events() if events is None else events
        return "\n".join(
            f"{e['id']} {e['date']} [{e['type']}/{e['certainty']}] ({e['topic']}) {e['summary']} "
            f"<- {', '.join('#' + str(i) for i in e['msg_ids'])}"
            for e in events
        )

    # ------------------------------------------------------------------ state (reduce)
    def state(self) -> dict:
        if self._state is not None:
            return self._state
        cached = self._cache_get("state.json")
        if cached is not None:
            self._state = cached
            return cached
        self._require_llm()
        parts = [self.header]
        if self.is_small:
            parts.append("RAW MESSAGES (source of truth):\n" + self.rendered)
        parts.append("LEDGER OF EXTRACTED EVENTS (time-ordered):\n" + self.ledger_text())
        self._log("building project state")
        data = self.llm.complete_json(prompts.STATE_SYSTEM, "\n\n".join(parts),
                                      "Build the current state of the project as JSON.",
                                      prompts.STATE_SCHEMA, max_tokens=6000)
        for section in ("decisions", "owners", "deadlines", "unassigned", "open_items"):
            for item in data.get(section, []) or []:
                item["msg_ids"] = clean_ids(item.get("msg_ids"), self.by_id)
        data["as_of"] = self.messages[-1].ts.strftime("%a %d %b %Y %H:%M")
        self._state = data
        self._cache_put("state.json", data)
        return data

    # ------------------------------------------------------------------ question answering
    def _retrieve(self, question: str) -> list[Message]:
        """Pick messages for a big chat: BM25 hits + messages behind matching ledger events + neighbours."""
        if self._bm25_msgs is None:
            self._bm25_msgs = BM25([m.text for m in self.messages])
        picked = {self.messages[i].id for i in self._bm25_msgs.top(question, 30)}
        if self.use_ledger:
            evs = self.events()
            ev_index = BM25([f"{e['topic']} {e['summary']}" for e in evs])
            for i in ev_index.top(question, 25):
                picked.update(evs[i]["msg_ids"])
        expanded = set()
        for mid in picked:
            expanded.update(range(mid - 2, mid + 3))
        return [m for m in self.messages if m.id in expanded]

    def build_context(self, question: str) -> str:
        parts = [self.header]
        if self.is_small:
            parts.append("CHAT MESSAGES (all of them):\n" + self.rendered)
        else:
            sel = self._retrieve(question)
            lines, prev = [], None
            for m in sel:
                if prev is not None and m.id != prev + 1:
                    lines.append("    ...")
                lines.append(render_message(m))
                prev = m.id
            parts.append(f"CHAT MESSAGES (the {len(sel)} most relevant of {len(self.messages)}; '...' marks gaps):\n"
                         + "\n".join(lines))
        if self.use_ledger:
            evs = self.events()
            ledger = self.ledger_text(evs)
            if len(ledger) > 25000:
                idx = BM25([f"{e['topic']} {e['summary']}" for e in evs])
                keep = sorted(idx.top(question, 60))
                ledger = self.ledger_text([evs[i] for i in keep])
            parts.append("LEDGER OF EXTRACTED EVENTS (hint only, may contain mistakes):\n" + ledger)
            st = self.state()
            compact = {k: st.get(k) for k in ("decisions", "owners", "deadlines", "unassigned", "open_items")}
            parts.append("DERIVED PROJECT STATE (hint only, may contain mistakes):\n"
                         + json.dumps(compact, ensure_ascii=False))
        return "\n\n".join(parts)

    def ask(self, question: str) -> VerifiedAnswer:
        self._require_llm()
        context = self.build_context(question)
        self._log(f"answering with {len(context)} chars of context")
        raw = self.llm.complete_json(prompts.ANSWER_SYSTEM, context, f"QUESTION: {question}\n\nAnswer as JSON.",
                                     prompts.ANSWER_SCHEMA, max_tokens=1500)
        return verify_answer(question, raw, self.messages)
