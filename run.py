#!/usr/bin/env python
"""Ask questions about a WhatsApp chat export.

  python run.py --chat data/team_chat.txt                       # interactive
  python run.py --chat data/team_chat.txt --ask "Who owns payments?"
  python run.py --chat data/team_chat.txt --state               # state-of-the-project report
  python run.py --chat data/team_chat.txt --offline --ask "payments"   # no LLM: show matching messages
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252; chats contain emoji
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from chatqa.llm import LLM, LLMError, config_from_env
from chatqa.parser import ParseError, parse_chat_file
from chatqa.pipeline import ChatQA
from chatqa.report import format_answer, format_state
from chatqa.retrieval import BM25


def offline_search(messages, question: str, k: int = 8) -> str:
    idx = BM25([m.text for m in messages])
    hits = sorted(idx.top(question, k))
    if not hits:
        return f"Q: {question}\nNo matching messages."
    lines = [f"Q: {question}", "(offline mode: no LLM, so no answer - these are the best-matching messages, in time order)"]
    for i in hits:
        m = messages[i]
        lines.append(f"  [#{m.id} | {m.stamp} | {m.sender or 'system'} | line {m.line}] {m.text.splitlines()[0][:150]}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Answer questions about a WhatsApp chat export, with evidence.")
    ap.add_argument("--chat", required=True, help="path to the exported chat .txt")
    ap.add_argument("--ask", action="append", metavar="QUESTION", help="question to answer (repeatable)")
    ap.add_argument("--state", action="store_true", help="print the state-of-the-project report")
    ap.add_argument("--out", help="also write the state report / answers to this file")
    ap.add_argument("--json", action="store_true", help="print answers as JSON")
    ap.add_argument("--offline", action="store_true", help="no LLM: show best-matching messages only")
    ap.add_argument("--no-ledger", action="store_true", help="answer from raw messages only (skip ledger/state)")
    ap.add_argument("--no-cache", action="store_true", help="recompute ledger/state instead of using .cache/")
    ap.add_argument("--provider", help="override LLM_PROVIDER (groq, gemini, openai, ollama, anthropic)")
    ap.add_argument("--model", help="override LLM_MODEL")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    try:
        messages = parse_chat_file(args.chat)
    except ParseError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"Loaded {len(messages)} messages from {args.chat} "
          f"({messages[0].ts:%d %b %Y} – {messages[-1].ts:%d %b %Y})", file=sys.stderr)

    if args.offline:
        for q in args.ask or []:
            print(offline_search(messages, q) + "\n")
        return 0

    try:
        cfg = config_from_env(args.provider, args.model)
    except LLMError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if cfg is None:
        print("error: no LLM configured. Copy .env.example to .env and set a key "
              "(e.g. GROQ_API_KEY or GEMINI_API_KEY), or run with --offline.", file=sys.stderr)
        return 2
    print(f"Using {cfg.label()}", file=sys.stderr)
    qa = ChatQA(messages, LLM(cfg, verbose=args.verbose), use_ledger=not args.no_ledger,
                use_cache=not args.no_cache, verbose=args.verbose)

    outputs: list[str] = []
    try:
        if args.state:
            report = format_state(qa.state(), messages, title=f"State of the project — {Path(args.chat).name}")
            print(report)
            outputs.append(report)
        if args.ask:
            answers = [qa.ask(q) for q in args.ask]
            if args.json:
                text = json.dumps([a.to_dict() for a in answers], ensure_ascii=False, indent=2)
                print(text)
                outputs.append(text)
            else:
                for a in answers:
                    text = format_answer(a)
                    print(text + "\n")
                    outputs.append(text)
        if not args.state and not args.ask:
            interactive(qa, messages)
    except LLMError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.out and outputs:
        Path(args.out).write_text("\n\n".join(outputs) + "\n", encoding="utf-8")
        print(f"(written to {args.out})", file=sys.stderr)
    return 0


def interactive(qa: ChatQA, messages) -> None:
    print("Ask a question (English or Hinglish). Commands: :state  :quit", file=sys.stderr)
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not q:
            continue
        if q in (":q", ":quit", "exit", "quit"):
            return
        try:
            if q == ":state":
                print(format_state(qa.state(), messages))
            else:
                print(format_answer(qa.ask(q)))
        except LLMError as e:
            print(f"error: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
