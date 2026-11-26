#!/usr/bin/env python
"""Run the hand-written test questions and auto-check the answers.

  python eval.py                                  # uses tests/eval_questions.json
  python eval.py --only 1,5,8 --no-ledger         # subset / ablation
Results go to eval_results/<label>.json and .md. The auto-check is coarse
(keywords + status + cited message ids); read the answers yourself too.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
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
from chatqa.parser import parse_chat_file
from chatqa.pipeline import ChatQA


def check(q: dict, a: dict) -> tuple[bool, list[str]]:
    text = (a["answer"] + " " + a.get("changed_over_time", "")).lower()
    problems = []
    for group in q.get("must_any", []):
        if not any(s.lower() in text for s in group):
            problems.append(f"missing one of {group}")
    if a["status"] not in q.get("expected_status", [a["status"]]):
        problems.append(f"status {a['status']} not in {q['expected_status']}")
    cited = {e["msg_id"] for e in a["evidence"]}
    if q.get("key_msgs") and not cited & set(q["key_msgs"]):
        problems.append(f"cites none of key messages {q['key_msgs']} (cited {sorted(cited)})")
    return not problems, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="tests/eval_questions.json")
    ap.add_argument("--chat")
    ap.add_argument("--only", help="comma-separated question ids")
    ap.add_argument("--no-ledger", action="store_true")
    ap.add_argument("--provider")
    ap.add_argument("--model")
    ap.add_argument("--label", help="name for the results files")
    ap.add_argument("--fresh", action="store_true", help="ignore previous results for this label")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    spec = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    chat = args.chat or spec["chat"]
    qs = spec["questions"]
    if args.only:
        wanted = {int(x) for x in args.only.split(",")}
        qs = [q for q in qs if q["id"] in wanted]

    cfg = config_from_env(args.provider, args.model)
    if cfg is None:
        print("No LLM configured (see .env.example).", file=sys.stderr)
        return 2
    label = args.label or (cfg.label().replace(":", "_").replace("/", "_") + ("_noledger" if args.no_ledger else ""))
    out_dir = Path("eval_results")
    out_dir.mkdir(exist_ok=True)
    out_json = out_dir / f"{label}.json"
    results = {} if args.fresh or not out_json.exists() else {
        r["id"]: r for r in json.loads(out_json.read_text(encoding="utf-8"))["results"]}

    msgs = parse_chat_file(chat)
    qa = ChatQA(msgs, LLM(cfg, verbose=args.verbose), use_ledger=not args.no_ledger, verbose=args.verbose)
    print(f"Evaluating {len(qs)} questions with {cfg.label()} (ledger={'off' if args.no_ledger else 'on'})", file=sys.stderr)

    for q in qs:
        if q["id"] in results and results[q["id"]].get("result"):
            continue
        try:
            a = qa.ask(q["question"]).to_dict()
        except LLMError as e:
            print(f"  Q{q['id']}: LLM error: {e} (re-run to resume)", file=sys.stderr)
            break
        ok, problems = check(q, a)
        results[q["id"]] = {"id": q["id"], "question": q["question"], "expected": q["answer"],
                            "result": a, "auto_pass": ok, "problems": problems}
        print(f"  Q{q['id']:>2} {'PASS' if ok else 'FAIL'}  {a['status']:<12} {a['answer'][:90]}", file=sys.stderr)
        out_json.write_text(json.dumps({"model": cfg.label(), "ledger": not args.no_ledger,
                                        "results": sorted(results.values(), key=lambda r: r["id"])},
                                       ensure_ascii=False, indent=2), encoding="utf-8")

    done = [r for r in results.values() if r.get("result")]
    passed = sum(r["auto_pass"] for r in done)
    md = [f"# Eval results: {cfg.label()} (ledger {'off' if args.no_ledger else 'on'})", "",
          f"Auto-check: **{passed} / {len(done)}** passed.", "",
          "| # | Question | Status | System answer | Cited | Auto | Problems |", "|---|---|---|---|---|---|---|"]
    for r in sorted(done, key=lambda r: r["id"]):
        a = r["result"]
        cited = ", ".join(f"#{e['msg_id']}" for e in a["evidence"])
        ans = a["answer"].replace("|", "/").replace("\n", " ")
        md.append(f"| {r['id']} | {r['question']} | {a['status']} | {ans} | {cited} | "
                  f"{'✅' if r['auto_pass'] else '❌'} | {'; '.join(r['problems']).replace('|', '/')} |")
    (out_dir / f"{label}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nAuto-check: {passed}/{len(done)} passed. Wrote {out_json} and {out_dir / (label + '.md')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
