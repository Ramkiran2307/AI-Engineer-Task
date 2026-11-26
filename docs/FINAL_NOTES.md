# Final Notes

## 1. How to run it

Needs Python 3.10+ (tested on 3.13, Windows 11).

```bash
git clone <this repo> && cd AI-Engineer-Task
pip install -r requirements.txt
cp .env.example .env        # then put ONE key in .env (see below)
```

`.env`. Pick one provider. Everything I tested used the free Gemini tier:

```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=...                    # free key: https://aistudio.google.com/apikey
LLM_MODEL=gemini-flash-lite-latest    # what the results below were produced with
```

Other options in `.env.example`: `groq` (`GROQ_API_KEY`), `anthropic` (`ANTHROPIC_API_KEY`, Claude via the official SDK), any OpenAI-compatible endpoint (`LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL`), or a local `ollama` (no key).

**Run it on any chat file:**

```bash
python run.py --chat path/to/chat.txt                       # interactive: type questions, ":state" for the report
python run.py --chat path/to/chat.txt --state               # state-of-the-project report (markdown)
python run.py --chat path/to/chat.txt --ask "Who owns payments?" --ask "Demo kab hai?"
python run.py --chat path/to/chat.txt --state --out state.md
python run.py --chat path/to/chat.txt --ask "..." --json    # machine-readable, with evidence
python run.py --chat path/to/chat.txt --offline --ask "payments"   # no key: just shows matching messages
```

Useful flags: `--model`, `--provider`, `--no-review` (skip the second checking pass: half the calls), `--no-ledger`, `--no-cache`, `-v`.

**Tests and eval:**

```bash
python -m pytest                       # 27 offline tests (parser, verifier, pipeline with a fake LLM)
python eval.py                         # runs the 18 hand-answered questions in tests/eval_questions.json
python eval.py --no-review --no-ledger # ablations; results land in eval_results/
```

Windows note: `run.py` forces UTF-8 output, so emoji in chats don't crash the console.

## 2. How it works (one paragraph)

First, plain code (no AI) reads the exported file and turns it into a numbered list of messages, each with its exact date, weekday, sender and line number. It glues multi-line messages back together, works out whether dates are day-first or month-first, and marks photos and deleted messages as "content not available". Then an AI model reads the whole chat once and writes a **ledger**: a time-ordered list of facts such as "20 Oct: payments switched to UPI QR (#51)" or "2 Nov: switched back to Razorpay test mode (#66)". From that ledger plus the chat, a second AI call builds the **current state**: decisions, who owns what, deadlines, and what's unassigned or open. The rule throughout is "later beats earlier", even when the earlier message said "final". When you ask a question, the AI gets the chat (or, for a huge chat, only the relevant parts) plus that state. It must answer in JSON with the message numbers and exact quotes it relied on. A second AI pass re-checks the draft claim by claim. Finally, plain code checks every citation against the real file: a quote that doesn't exist is thrown out, and an answer left with no real evidence is replaced by "the chat doesn't say". The evidence you see is printed from the file itself, never from the AI's text, so it can't show a made-up timestamp.

```
chat.txt → [parser] → messages → [LLM: ledger] → [LLM: state] ─┐
question ──────────────────────→ [retrieve if big] → [LLM: answer] → [LLM: review] → [code: verify citations] → answer + evidence
```

## 3. My test set and results

18 questions (`tests/eval_questions.json`). I worked out the answers by hand from the chat **before** running anything. Results are from the final code with `gemini-flash-lite-latest` (full pipeline: ledger + state + review + verifier); raw output is in `eval_results/final_flashlite.json`. "Correct?" is **my manual grade**. The automatic keyword check is coarse and wrong in both directions (see Q10, Q12).

| # | Question | Correct answer (by hand) | System's answer (shortened) | Correct? | Notes |
|---|---|---|---|---|---|
| 1 | What payment method are we using for the demo? | Razorpay **test mode** (#66, 2 Nov), after UPI QR on 20 Oct (#51) | Razorpay test mode; history: Razorpay → UPI QR (20 Oct, KYC) → back to Razorpay test mode (2 Nov). Cites #66, #62 | ✅ | The "two finals" trap. Naive keyword search gets this wrong (see §4) |
| 2 | Who is responsible for payments now, and did they finish it? | Kabir (#67); checkout works but webhook pending (#86), so not finished | Kabir; checkout integrated, webhook still pending. Cites #62, #67, #86 | ✅ | |
| 3 | When is demo day? | Thu 26 Nov 2026 (#79/#80); was 4 Dec, then 27 Nov | Thursday 26 Nov 2026; history 4 Dec → 27 Nov → 26 Nov (typo) | ✅ | |
| 4 | When is the report due? | 23 Nov (#81), derived from "3 days before demo" (#28) | 23 Nov 2026; history 1 Dec → 24 Nov → 23 Nov | ✅ | |
| 5 | Who is working on the search feature? | Nobody: Kabir dropped it (#44), still unowned 10 Nov (#87), on 14 Nov agenda | Unassigned; Kabir dropped it; not assigned to anyone since. Cites #44, #87, #97 | ✅ | |
| 6 | Is there anything nobody is working on? | Search | Yes, search; Kabir dropped it, attempts to give it to Priya/others failed | ✅ | |
| 7 | Who owns auth, and is it done? | Kabir (handover #54); done & merged (#85) | Kabir; done and merged; history Rohan → Kabir 24 Oct | ✅ | |
| 8 | Rohan ne tests complete kar diye kya? *(Hinglish)* | Nahi: still pending, promised "by this Sunday" (#84), earlier misses (#78) | "Nahi, Rohan ke tests abhi complete nahi hue hain… Sunday tak kar dega" | ✅ | Answered in Hinglish, as asked |
| 9 | Which domain did we buy, from where, how much? | campuscart.in, Namecheap, Rs 650 (#38, #40), not GoDaddy Rs 800 | campuscart.in from Namecheap for Rs 650 | ✅ | |
| 10 | Where are we deploying, and is the app live yet? | Render (#61). Target 15 Nov (#83); **chat doesn't say if it's live** | Render, ready by 15 Nov. "**The app is not live yet.**" | ❌ | Over-claims from a plan. Auto-check passed it, but I don't |
| 11 | What did the team decide about search at the 14 Nov meeting? | Chat doesn't say (ends 12 Nov) | NOT IN CHAT: meeting is after the last message | ✅ | |
| 12 | Which logo did we finalise? | None; only Meera's preference (#101) | No logo finalised; Priya shared 2, Meera prefers blue, no group decision | ✅ | Auto-check marked ❌ (wording "does not finalize" not in my keyword list) |
| 13 | Backend aur database ke liye kya decide hua tha? *(Hinglish)* | Django (+React) (#12), Postgres (#15) | "Backend ke liye Django aur database ke liye Postgres" | ✅ | |
| 14 | What is Meera responsible for now? | Report + PPT fully (#68); payments moved to Kabir | Report and PPT; payments went to Kabir | ✅ | |
| 15 | What is the total budget of the project? | Chat doesn't say (only domain Rs 650) | NOT IN CHAT: only the domain cost (Rs 650) is mentioned | ✅ | An earlier version said "total budget is Rs 650" (see §4) |
| 16 | Is Kabir coming to the Saturday meeting? | Not in person (family function), joins on call (#96) | Not in person, will join via call | ✅ | |
| 17 | Did Aarav confirm he is attending? | Yes: "obviously 😂" (#102) answers Rohan's #100, not Meera's logo msg | Yes, replying to Rohan's question. Cites #100, #102 | ✅ | The interleaved-reply trap |
| 18 | Priya abhi kis cheez pe kaam kar rahi hai? *(Hinglish)* | Seller dashboard (#58/#89); listings+filters done | "seller dashboard pe… listing page aur filters ka kaam khatam" | ✅ | |

**Overall: 17 / 18 correct** (my grade). The automatic check reports 18/18, which is too generous on Q10.

**Same 18 questions, other configurations** (same model, my manual grade):

| Configuration | Manual | What went wrong |
|---|---|---|
| Full pipeline (above) | **17/18** | Q10 over-claim |
| No review pass | 16/18 | Q10; Q5 says the team "tried to assign search to Meera" (never happened) |
| No ledger/state, no review (≈ "whole chat to the LLM" + my verifier) | 16/18 | Q10; Q6 says "Meera declined" search (she didn't) |
| Full pipeline, **forced retrieval** (pretend the chat is too big; model sees only a slice) | 17/18 | Q6 withheld: the draft invented both quotes, so the verifier blocked it. Q10 correct this time |
| Earlier version, `gemini-3-flash-preview`, before the language fix and review pass | 16/18 | Q15 "total budget is Rs 650"; Q10 |

**A chat it had never seen.** I wrote `tests/fixtures/hackathon_chat_ios.txt`: a different team and app, iOS format with `[brackets]`, 24-hour time and seconds. It has its own framework reversal, backend handover, deadline extension and unowned task. 6/6 questions were correct: framework (React Native, after dropping Flutter), backend owner in Hinglish (Dev, after Sara's exams), deadline (16 Feb, extended from 14 Feb), demo video (nobody), "did Arjun finish the map screen?" (no: an API key issue, after promising "kal tak"), and "who won?" (not in chat). Reports for both chats are in `docs/sample_output/`.

Honest caveat: 18 questions is a small set, and I wrote them knowing the traps. The gap between configurations (17 vs 16) is one question, which is within run-to-run noise. Flash-lite at temperature 0 still gave different answers to the same question across runs.

## 4. What it still gets wrong, and why

1. **Turning a plan into a status (Q10, "the app is not live yet").** Aarav said on 9 Nov "15 Nov tak ready". The chat ends 12 Nov, so nobody knows. The model reasons "target is in the future, so not live" and states it as fact. There is an explicit prompt rule against this, and the review pass sometimes fixes it (the forced-retrieval run got it right), but not reliably on flash-lite. **Cause:** the verifier only checks that citations are real. It can't check that the *inference* drawn from a real message is valid. A stronger model would likely help, but I couldn't confirm that: the stronger Gemini model's free quota is 20 requests/day.
2. **Invented quotes on retrieval runs (forced-retrieval Q6).** The model wrote Hinglish-sounding quotes that don't exist in the chat ("Main nahi kar paunga, koi aur dekh lo"). The verifier caught it and withheld the answer, which is safe, but the user loses a correct answer. **Cause:** weak models paraphrase into "quote" fields, especially when the context is fragmented.
3. **Small errors in side details and in the state report.** A history entry "Django + React + SQLite" (SQLite was only asked about, #13). The report deadline is labelled "confirmed" though it was derived from a rule. In the hackathon chat, the pitch deck is "not started" when the chat just says nothing. Ablation runs added "Meera declined search". **Cause:** the state and history are free text written by the LLM. Only their message ids are checked, not each sentence.
4. **Citations are sometimes "near misses".** For example, Q15 in one run cited Meera's "Rs 800 theek hai" (#36) for the Rs 650 fact. The verifier accepts any real message with a matching quote; it doesn't judge whether that message is the *best* support.
5. **The automatic eval checker is coarse.** It uses keyword lists, so it passed Q10 and failed a correct Q12. I grade by hand. A better checker would be an LLM judge with my reference answers, checked against my manual grades.
6. **Untested paths.** The Anthropic backend is written to the SDK docs but has never been executed (no key, and no test covers it). Groq is configured but not run. The big-chat path was tested by *forcing* this chat through it (`FULL_CONTEXT_CHARS=3000`), not on a real 10,000-message export. Retrieval is BM25 over words, so a question phrased with words that never appear in the chat ("vendor" vs "Razorpay") relies on the ledger summaries to bridge the gap.
7. **Parser edge cases.** Multi-line messages whose continuation line itself starts with a date-and-time would be split. System lines are detected with English-only phrases ("created group", "added"), so exports in another UI language would show those as normal messages from a person.
8. **One bug I introduced and found through the eval.** My Hinglish detector counted "the" and "me" as Hindi words, so "What is **the** total budget of **the** project?" was treated as Hinglish and answered in Hinglish. Fixed, with a regression test.

## 5. What I'd do with 2 more days

1. **Check inferences, not just citations.** Add a claim-level check: split the answer into atomic claims and verify each one against its cited message with a separate entailment call ("does #83 *support* 'the app is not live'?"), marking the unsupported ones. This targets my only remaining eval failure (Q10) and failure types 1, 3 and 4 above, which are the "confidently wrong" kind the brief says is worst.
2. **A bigger, blind test set and an LLM judge.** Get 50+ questions over 2–3 chats written by someone else, including a long real export. Score with an LLM judge against reference answers, and calibrate the judge on my manual grades. I'd do this before more tuning, because with 18 questions I can't tell a real improvement from noise.
3. **Make the state structured where code can check it.** Have the ledger emit `supersedes: e12` links and owner/status fields. Then "current owner" and "latest decision" could be computed by code from the newest event, instead of trusting free text, which would remove errors like the SQLite history line. Third, because it's the biggest change and only pays off once 1 and 2 can measure it.

## 6. What I learned that I didn't know on day one

- "Final" means nothing in a group chat. Time order is the only reliable signal, and the hard part is noticing the *later* message that never uses the topic's keyword (02/11 "Razorpay test mode final" never says "payment").
- Real-looking citations aren't enough. The model can cite a real message and still draw a wrong conclusion from it ("Rs 650" → "total budget Rs 650"). Checking citations in code stops invented evidence; it doesn't stop bad reasoning.
- My own evaluation tooling had bugs (the language detector, a too-lenient keyword checker). Reading every answer by hand found things the auto-score hid.
- Free LLM tiers are an engineering constraint: models get retired (the `gemini-2.5-flash` default stopped working mid-project), overloaded (503s) or capped at 20 requests/day. Caching the ledger/state per chat, failing fast on daily quotas, and resumable evals all came out of that.
- WhatsApp exports differ more than I expected: day-first vs month-first dates that only become clear later in the file, invisible Unicode marks, and a narrow no-break space before "PM".

## 7. What I understand deeply vs. what I accepted from AI

> **TODO (owner):** rewrite this section in your own words before submitting; it's a personal statement. The facts below are accurate about how the code was produced.

I built this together with an AI coding assistant (Claude Code). I directed the work, ran it, read the results and made the calls.

- **Designed / can fully explain:** the decomposition and the list of traps in the data; the pipeline (parser → ledger → state → answer → review → verifier); the rule that evidence is printed from the file and never from the model; why the verifier downgrades unsupported answers; the hand-written answer key and the manual grading; and the conclusions from the ablations.
- **Written with AI help and checked by tests and reading:** the parser regexes and date-order detection (`tests/test_parser.py`), BM25 retrieval, the provider HTTP client, retry and backoff, and the prompts (iterated against eval failures).
- **Accepted with less depth:** the exact Anthropic SDK call shape (structured-output and fallback parameters taken from the SDK docs, not run live); the BM25 constants (k1 = 1.4, b = 0.75 are textbook defaults, not tuned).

## 8. Demo video

Link to your 3-minute screen recording: **TODO: add link**
