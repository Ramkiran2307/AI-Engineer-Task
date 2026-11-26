# Decomposition (written before any code)

## 1. The problem in my own words

A team's WhatsApp group is the only record of their project, and it is messy: plans get proposed, agreed, reversed and re-agreed, tasks move between people, and deadlines shift. I need to build a tool that reads an exported chat file (any chat in this format, not just this one) and answers plain-English or Hinglish questions about it, such as "who owns payments?" or "when is the demo?". Each answer must point to the exact messages it came from. When the chat does not contain the answer, the tool must say so instead of guessing. It also has to produce a one-page "state of the project": the current decisions, who owns what, and what is still open or has no owner.

The core difficulty is not finding messages that mention a topic. It is working out which of several conflicting messages is the **current** truth.

## 2. What I noticed in the data

| # | What I noticed (quote + timestamp) | Why it makes answering hard |
|---|---|---|
| 1 | **Payments were reversed twice, and both versions say "final".** `20/10/26 8:16 PM Aarav: agreed. final decision: no Razorpay, UPI QR manual`, then `02/11/26 8:49 PM Aarav: haan. Razorpay test mode final. QR wala scrap.` | The word "final" appears in both the old and the new decision, so a system can't trust it. The only thing that settles it is time order: the later message wins. Keyword search for "final decision" returns the **wrong** (older) one first, because it contains the exact phrase. |
| 2 | **The demo date changed twice, and the report deadline is derived from it.** `12/10/26 7:30 PM Meera: ... Demo day 4 Dec so report 1 Dec` → `05/11/26 6:10 PM Aarav: ... ab 27 Nov (Friday)` → `09/11/26 5:30 PM Priya: Correction. ... Demo day 26 Nov (Thursday), 27 nahi. Notice mein typo tha` | There are three candidate demo dates. The report deadline (23 Nov) is never stated by the college. Meera works it out from a rule ("report due 3 days before demo day") that appears once, on 12/10. On 05/11 the derived date (24 Nov) came with "haan shayad" (maybe), so it wasn't firm. A good answer gives the current value, says it is derived, and mentions the history. |
| 3 | **Ownership moves, and a handover spans several messages, one of them a question.** `24/10/26 11:20 PM Rohan: ... auth Kabir le sakta hai?` → `11:22 PM Kabir: mere paas chat hai already...` → `11:25 PM Kabir: arre theek hai, auth bhi le leta hoon. but Rohan you do the DB schema and the tests then` → `11:26 PM Rohan: deal.` Also `02/11/26 8:50 PM Kabir: payments ab mere paas, Meera tum report pe focus karo` | The original split on 05/10 says "Rohan - auth" and "Meera - payments". Both are now wrong. The auth handover is a question, then reluctance, then acceptance with a counter-offer: no single message holds the full fact. Kabir now owns auth, chat and payments (he says so himself at `05/11/26 6:20 PM`), and Rohan picked up schema and tests, which weren't in the original split. |
| 4 | **"Nobody owns search" can only be found by noticing an absence.** `05/10/26 8:02 PM` split gives search to Kabir → `19/10/26 6:16 PM Kabir: chat main kar lunga. search koi aur le lo please` → `10/11/26 9:14 PM Priya: search ka kya? abhi bhi koi nahi le raha` → Priya declines (9:16), Rohan defers (9:18: "search Saturday ko discuss karte hain"). The chat ends on 12/11, **before** the 14 Nov meeting. | To answer "is anything unassigned?" the system must track ownership over time and see that search was dropped and never picked up. Searching for "search" finds the original assignment "Kabir - search" first. The correct answer is "unassigned as of the last message; it was on the 14 Nov meeting agenda, but the chat doesn't say what was decided there". |
| 5 | **Promises are not completions, and teammates flag it with sarcasm.** `12/10/26 7:35 PM Rohan: auth kal tak khatam. promise` / `7:36 PM Priya: Sure Rohan, "kal tak" 🙄 you said that last week too`. Tests: `06/11 11:06 PM "tests kal raat tak kar dunga"` → `07/11 11:50 PM "sorry yaar, tests nahi ho paye. kal pakka"` → `09/11 5:40 PM "tests ab bhi pending hain, I'll do by this Sunday"` | "Will do by X" must not be read as "done". The latest status of tests is "pending, promised by Sunday 15 Nov" and nothing confirms they were finished. Auth was never finished by Rohan at all; Kabir finished it on `10/11/26 9:12 PM "auth done, merged"`. |
| 6 | **Hinglish words that look like English mean something else.** `05/10/26 8:02 PM` split line `Main - deployment` (here "main" = "I", i.e. Aarav, the sender), `19/10/26 6:16 PM "chat main kar lunga"` (I'll do chat). Also `"kal"` means both tomorrow and yesterday. | A naive reader could think there is a person called "Main", or that "main" means "the main feature". Ownership in the split message is relative to its **sender**. |
| 7 | **Relative dates need the message's own date and the weekday.** `09/11/26 5:40 PM "I'll do by this Sunday"`, `10/11/26 9:18 PM "search Saturday ko discuss karte hain"`, `12/10/26 7:35 PM "auth kal tak"` | "This Sunday" from Mon 9 Nov 2026 is 15 Nov. The system has to know that 09/11/26 is a Monday, which the file never states. If the model only sees "09/11/26" it may misread it (DD/MM vs MM/DD) and get weekdays wrong. |
| 8 | **The date format is ambiguous, and some messages run over several lines.** `03/10/26` could be 3 Oct or 10 Mar; only later lines like `16/10/26` prove it's DD/MM/YY. The task split at `05/10/26 8:02 PM` is one message spread over 6 lines. | The parser must work out the date order from the whole file, not per line, and attach continuation lines to the previous message. Otherwise "Rohan - auth" becomes a line with no sender or time. Another chat could use MM/DD, a 24-hour clock or `[brackets]`, so I can't hard-code this one. |
| 9 | **Some content is simply missing: media, deleted and edited messages.** `16/10/26 9:51 PM Aarav: <Media omitted>` (the receipt), `9:55 PM Aarav: This message was deleted`, `16/10/26 9:07 PM Meera: Rs 800 theek hai ... <This message was edited>`, `12/11/26 8:11 PM Priya: <Media omitted>` (logo options) | "How much did the domain cost?" The visible numbers are Rs 800 (GoDaddy, which Meera OK'd) and Rs 650 (Namecheap, which Aarav says he bought). The answer is Rs 650, and the receipt itself isn't readable. "Which logo did we pick?" Only Meera's opinion ("blue wala") exists; there is no decision. The system has to say "not decided" and not turn one opinion into a decision. |
| 10 | **Replies interleave, so "who said yes to what" isn't the line above.** `12/11/26 8:11 PM Priya: logo ke liye 2 options...` / `8:12 PM Rohan: Aarav you're also coming right?` / `8:12 PM Meera: second wala better lag raha, blue wala` / `8:13 PM Aarav: obviously 😂` | Aarav's "obviously" answers Rohan's question about the meeting, not the logo. Meera's "second wala" is about the logo, not the meeting. Adjacency is not threading. |
| 11 | **Some questions about the future have no answer in the chat.** `09/11/26 5:34 PM Aarav: Render pe deploy kar raha hoon, 15 Nov tak ready` and the 14 Nov meeting. | The chat stops on 12/11. "Is the app deployed?" and "Who took search at the meeting?" can't be answered. The tool must say "the chat doesn't say" and give the latest known state ("planned on Render, target 15 Nov"). |

## 3. The simplest thing that could work, and how it would fail

**Dumbest reasonable approach:** split the file into lines, find the 5 lines that share the most words with the question (keyword match), paste them into an LLM and ask it to answer.

Three questions it would get wrong:

1. **"What payment method are we using?"** The keyword "payment" plus "final decision" pulls up `20/10 8:16 PM "final decision: no Razorpay, UPI QR manual"`. The reversal at `02/11 8:49 PM "Razorpay test mode final. QR wala scrap."` doesn't contain the word "payment", so it may never be retrieved. The LLM confidently answers "UPI QR", which is wrong.
2. **"Who is working on search?"** The top match is the original split line containing "Kabir - search". The message where Kabir gives it up (`19/10 6:16 PM`) and the later "abhi bhi koi nahi le raha" both use the same word, but top-5 by word overlap can't tell old from new and doesn't order by time. Likely answer: "Kabir", which is wrong. The truth is that nobody owns it.
3. **"When is the report due?"** Lines containing "report" include `12/10 "report 1 Dec"`, `05/11 "24 Nov?"` and `09/11 "toh report 23 Nov"`. Without the dates and the demo-day correction, the model might pick 1 Dec or 24 Nov. The line-splitting parser also breaks the multi-line task split, so "Meera - payments + report/PPT" loses its sender and timestamp.

A second "simple" approach is to paste the whole chat into an LLM. That works better on a 107-line chat, but it (a) doesn't scale to a long chat, (b) has no checkable evidence, so the model can invent a timestamp, and (c) still tends to grab the first "final" it sees. My design keeps whole-chat context when the chat is small, and adds the pieces that fix (a) to (c).

## 4. Break it into sub-problems

```
                 chat.txt (any WhatsApp export)
                          │
                ┌─────────▼──────────┐
           [A]  │  Parser            │  regex + format detection (DD/MM vs MM/DD, 12h/24h,
                │                    │  multi-line, system / media / deleted / edited)
                └─────────┬──────────┘
                          │  List[Message{id, line, datetime, weekday, sender, text, flags}]
                ┌─────────▼──────────┐
           [B]  │  Renderer          │  "[#42 | Mon 09 Nov 2026 17:40 | Rohan] tests ab bhi ..."
                └─────────┬──────────┘  (absolute dates + weekday so "this Sunday" is resolvable)
          ┌───────────────┼──────────────────────┐
┌─────────▼────────┐      │             ┌────────▼──────────┐
│ [C] Ledger       │      │             │ [D] Retriever      │ (only if chat is too big for
│ extraction (LLM) │      │             │ BM25 + neighbours  │  one prompt; otherwise "all")
│ per chunk → JSON │      │             └────────┬──────────┘
│ events w/ msg ids│      │                      │
└─────────┬────────┘      │                      │
┌─────────▼────────┐      │                      │
│ [E] State builder│      │                      │
│ (LLM reconcile,  │      │                      │
│ later beats      │      │                      │
│ earlier)         │      │                      │
└─────────┬────────┘      │                      │
          │ state.json    │                      │
          ▼               ▼                      ▼
 [G] State-of-project   ┌──────────────────────────────┐
     report (markdown)  │ [F] Answerer (LLM)           │◄── question (EN / Hinglish)
                        │ context = state + timeline + │
                        │ relevant messages            │
                        │ → JSON {status, answer,      │
                        │   evidence[msg_id, quote],   │
                        │   history}                   │
                        └──────────────┬───────────────┘
                              ┌────────▼─────────┐
                         [H]  │ Evidence verifier│  msg ids exist? quote really in message?
                              │ (deterministic)  │  no valid evidence → "chat doesn't say"
                              └────────┬─────────┘
                                       ▼
                         answer + citations printed FROM THE PARSED FILE
```

**[A] Parser**
- Input: raw `.txt` export.
- Output: list of `Message` objects. Continuation lines are joined to the previous message. System lines (encryption notice, "created group", "added") are flagged. `<Media omitted>`, "This message was deleted" and `<This message was edited>` are flagged, with the edit tag stripped from the text.
- How I'll know: unit tests. This chat must parse to exactly the expected number of messages. The 05/10 8:02 PM message must contain all 6 lines. 03/10/26 must become 3 Oct 2026, not 10 Mar. Synthetic files in MM/DD, 24-hour and bracket `[dd/mm/yy, hh:mm:ss]` formats must also parse.

**[B] Renderer**
- Input: messages.
- Output: one compact line per message, with id, absolute date, weekday, sender and text.
- How I'll know: a test that 09/11/26 renders as "Mon 09 Nov 2026", and that ids are stable and unique.

**[C] Ledger extraction (LLM)**
- Input: rendered messages, in chunks with overlap for long chats.
- Output: JSON events `{type: decision|assignment|status|deadline|commitment|open_question|info, topic, summary, people, msg_ids}`.
- How I'll know: the payments reversal shows up as separate events (Razorpay → dropped → back to Razorpay), each pointing to the right message ids. Every msg id exists (checked in code).

**[E] State builder (LLM reconcile + code checks)**
- Input: the full event ledger, ordered by time.
- Output: `state.json` with current decisions (with superseded history), owners per workstream with status, deadlines, open questions and unassigned work. Every item has message ids.
- How I'll know: on this chat the state must say Razorpay test mode, Kabir owns auth, chat and payments, search is unassigned, demo is 26 Nov and report is 23 Nov. I check those by hand against my answer key in FINAL_NOTES.

**[D] Retriever**
- Input: question, messages.
- Output: the ids of relevant messages. If the whole chat fits the budget, it returns all of them, which is safest. Otherwise it returns the BM25 top-k with neighbouring messages.
- How I'll know: on a synthetic long chat (this one repeated with noise), the payments reversal message is still retrieved for "payment method?".

**[F] Answerer (LLM)**
- Input: question, the state, the event timeline, and the relevant raw messages.
- Output: strict JSON with status `answered | partial | not_in_chat`, the answer in the question's language, evidence `[{msg_id, quote}]`, and the history of changes.
- How I'll know: my 10+ hand-made questions, scored by a small eval script (must-contain / must-not-contain checks) plus my manual review.

**[H] Evidence verifier (no LLM)**
- Input: answer JSON, messages.
- Output: the answer with only valid evidence kept. Citations are printed from the parsed file, never from LLM text. If the status is "answered" but no valid evidence is left, the answer is downgraded to "the chat doesn't say".
- How I'll know: unit tests with a fake LLM that returns a made-up msg id or a made-up quote. The output must drop it and downgrade.

**[G] State report**
- Input: `state.json` and messages.
- Output: a readable markdown "State of the project", with citations for each line.
- How I'll know: I read it next to my hand-made answer key.

## 5. What I don't know yet

| Unknown | How I'll find out |
|---|---|
| All the variants of the WhatsApp export format (iOS vs Android, 24h, seconds, brackets, locale-specific separators, the narrow no-break space before "PM"). | Look up examples, ask an AI for the variants and then **verify** with synthetic test files in my parser tests. |
| Whether one LLM call can reliably return valid JSON with correct message ids. | Experiment. Validate the JSON in code, retry once on a parse failure, and drop invalid ids. |
| How big a chat can go into a single prompt before quality drops or it gets too expensive. | Measure characters and tokens on this chat. Set a budget (≈ 60k chars) and switch to chunked ledger + retrieval above that. |
| Whether the LLM resolves "later wins" correctly when both messages say "final". | Test on the payments and demo-date questions. If it fails, put explicit "supersedes" history into the ledger and order the state by time in code. |
| Which LLM provider the reviewers will have a key for. | Support Anthropic, plus any OpenAI-compatible endpoint (OpenAI, Groq, Gemini, local Ollama) through env vars, so it isn't tied to one vendor. |
| How the unseen interview chat differs (other languages, more people, longer). | I can't know. I'll avoid anything chat-specific in code or prompts: no names, no topics like "payments" hard-coded. |

## 6. Build order

1. **Slice 1, the smallest end-to-end version:** parser → render the whole chat → one LLM call → print the answer. No ledger, no verification. This proves the CLI, the env setup and the parser on the real file.
2. **Slice 2, evidence and honesty:** strict JSON output with msg ids and quotes, the deterministic verifier, and "the chat doesn't say" when there's no evidence. I do this second because trust (point 2 and 3 of the spec) matters more than cleverness.
3. **Slice 3, the state of the project:** the ledger extraction, the state builder and the markdown report (`--state`). Answers then also get the state and timeline as context, which helps "current vs old" questions.
4. **Slice 4, scale:** chunked extraction and BM25 retrieval for chats too long for one prompt. It isn't needed for this chat, but the interview chat may be bigger.
5. **Slice 5, evaluation:** my 10+ question answer key, an eval script, honest scoring and fixing the worst failures.

The order is chosen so I always have something that runs, and each step addresses the biggest remaining risk to a *correct and trustworthy* answer.

## 7. Where I'll use AI, and where I won't

- **AI inside the product:** the LLM does the language understanding: Hinglish, sarcasm, a question followed by acceptance as a handover, "later beats earlier". Regex can't do these well.
- **Not AI inside the product:** parsing, date handling, weekday computation, retrieval, and above all **evidence checking**. The final citations are printed from the parsed file by code, so the model can't invent a timestamp.
- **AI as a coding assistant:** I'll let AI help write the parser regexes, the BM25 function and the boilerplate for the provider client, then check them with my own tests. I designed the data model myself (Message → events → state), along with the verifier rules and the test answer key, because those decide whether answers can be trusted. I also read the whole chat myself and worked out the correct answers by hand before running anything.
