# Eval results: gemini:gemini-flash-lite-latest (ledger on, review on)

Auto-check: **17 / 18** passed.

| # | Question | Status | System answer | Cited | Auto | Problems |
|---|---|---|---|---|---|---|
| 1 | What payment method are we using for the demo? | answered | The group is using Razorpay in test mode for the demo, which does not require business KYC. | #66, #62, #51 | ✅ |  |
| 2 | Who is responsible for payments now, and did they finish it? | answered | Kabir is currently responsible for payments. He has integrated the checkout using Razorpay test mode, but it is not fully finished yet because the payments webhook is still pending. | #67, #62, #86 | ✅ |  |
| 3 | When is demo day? | answered | Demo day is on 26 November 2026. | #80, #79, #69 | ✅ |  |
| 4 | When is the report due? | answered | The report is due on 23 November 2026. | #28, #72, #81 | ✅ |  |
| 5 | Who is working on the search feature? | answered | The search feature is currently unassigned. Kabir dropped it, and Priya declined to take it on, so deciding who will work on it is on the agenda for the upcoming team meeting. | #17, #44, #89, #97 | ✅ |  |
| 6 | Is there anything nobody is working on? | answered | Yes, the search feature is currently unassigned because Kabir dropped it due to the complexity of the chat feature, and nobody has taken it over yet. | #44, #87, #91 | ✅ |  |
| 7 | Who owns auth, and is it done? | answered | Auth is owned by Kabir, and it is done and merged. | #85, #54, #17 | ✅ |  |
| 8 | Rohan ne tests complete kar diye kya? | answered | Nahi, Rohan ke tests abhi complete nahi hue hain. Usne bataya hai ki tests abhi bhi pending hain aur woh is Sunday tak kar dega. | #84 | ✅ |  |
| 9 | Which domain did we buy, from where, and how much did it cost? | answered | The team bought the domain campuscart.in from Namecheap for Rs 650. | #35, #37, #38, #40 | ✅ |  |
| 10 | Where are we deploying, and is the app live yet? | answered | The team is deploying on Render, with Aarav planning to have it ready by 15 Nov 2026. The app is not live yet. | #61, #83, #60 | ✅ |  |
| 11 | What did the team decide about search at the Saturday 14 Nov meeting? | not_in_chat | The chat does not say what the team decided about search at the Saturday 14 Nov meeting, because the meeting is scheduled for 14 Nov and the chat ends on 12 Nov before it took place. However, the chat notes that deciding who will handle search is on the agenda for that upcoming meeting, as it remained unassigned after Kabir dropped it. | #92, #97 | ✅ |  |
| 12 | Which logo did we finalise? | not_in_chat | The chat does not state that a logo was finalised. Priya shared two options, and Meera expressed a preference for the second blue one, but the chat ends before any final decision is made. | #98, #101 | ❌ | missing one of ['not final', 'no logo', "hasn't", 'has not', 'not been', "doesn't say", 'does not say', 'no decision', 'not decided', 'undecided', "doesn't finalize", 'not yet', 'nahi'] |
| 13 | Backend aur database ke liye kya decide hua tha? | answered | Backend ke liye Django aur database ke liye Postgres decide hua tha. | #12, #15 | ✅ |  |
| 14 | What is Meera responsible for now? | answered | Meera is currently responsible for the report and presentation (PPT). | #17, #68 | ✅ |  |
| 15 | What is the total budget of the project? | not_in_chat | The chat doesn't mention a total project budget. It only notes the cost of purchasing the domain campuscart.in for Rs 650. | #38 | ✅ |  |
| 16 | Is Kabir coming to the Saturday meeting? | answered | Kabir cannot attend the Saturday meeting in person due to a family function, but he will join via call. | #96 | ✅ |  |
| 17 | Did Aarav confirm he is attending the Saturday meeting? | answered | Yes, Aarav confirmed he is attending the Saturday meeting when Rohan asked him, responding with "obviously" and laughing emojis. | #100, #102 | ✅ |  |
| 18 | Priya abhi kis cheez pe kaam kar rahi hai? | answered | Priya abhi seller dashboard par kaam kar rahi hai (listing page aur filters ka kaam already complete ho chuka hai). | #58 | ✅ |  |
