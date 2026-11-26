# Eval results: gemini:gemini-flash-lite-latest (ledger on)

Auto-check: **16 / 18** passed.

| # | Question | Status | System answer | Cited | Auto | Problems |
|---|---|---|---|---|---|---|
| 1 | What payment method are we using for the demo? | answered | The team is using Razorpay in test mode for the demo. | #62, #66 | ✅ |  |
| 2 | Who is responsible for payments now, and did they finish it? | answered | Kabir is currently responsible for payments. He has integrated the checkout using Razorpay test mode, but it is not fully finished yet because the webhook is still pending. | #67, #62, #86 | ✅ |  |
| 3 | When is demo day? | answered | Demo day is on Thursday, 26 November 2026. | #79, #80 | ✅ |  |
| 4 | When is the report due? | answered | The report is due on Monday, 23 Nov 2026. | #81, #80, #28 | ✅ |  |
| 5 | Who is working on the search feature? | answered | Nobody is currently working on the search feature; it is unassigned after Kabir dropped it due to the complexity of the chat feature. | #44, #87, #97 | ✅ |  |
| 6 | Is there anything nobody is working on? | answered | Yes, the search feature currently has no owner because Kabir dropped it due to the complexity of the chat feature, and nobody else has taken it yet. | #44, #87, #97 | ✅ |  |
| 7 | Who owns auth, and is it done? | answered | Kabir owns the auth workstream, and it is done and merged. | #85, #54, #17 | ✅ |  |
| 8 | Rohan ne tests complete kar diye kya? | answered | Nahi, Rohan ke tests abhi complete nahi hue hain. Chat ke anusar tests abhi pending hain aur Rohan ne unhe is Sunday tak karne ka promise kiya hai. | #84, #78 | ✅ |  |
| 9 | Which domain did we buy, from where, and how much did it cost? | answered | The team bought the domain campuscart.in from Namecheap for Rs 650. | #38, #40, #35 | ✅ |  |
| 10 | Where are we deploying, and is the app live yet? | answered | The team is deploying on Render, and the app is not live yet (Aarav plans to have it ready by 15 Nov). | #61, #83, #59 | ✅ |  |
| 11 | What did the team decide about search at the Saturday 14 Nov meeting? | not_in_chat | The chat doesn't say what the team decided about search at the Saturday 14 Nov meeting because the meeting is only planned for 14 Nov and no messages exist after Thu 12 Nov 2026. | #92 | ✅ |  |
| 12 | Which logo did we finalise? | answered | The team finalized the second option, which is the blue logo. | #98, #101 | ❌ | missing one of ['not final', 'no logo', "hasn't", 'has not', 'not been', "doesn't say", 'does not say', 'no decision', 'not decided', 'undecided', "doesn't finalize", 'not yet', 'nahi'] |
| 13 | Backend aur database ke liye kya decide hua tha? | answered | Backend ke liye Django aur database ke liye Postgres decide hua tha. | #8, #9, #12, #15 | ✅ |  |
| 14 | What is Meera responsible for now? | answered | Meera is currently responsible for the project report and presentation (PPT) fully. | #17, #68 | ✅ |  |
| 15 | What is the total budget of the project? | partial | Chat mein poore project ke total budget ke baare mein koi exact figure nahi bataya gaya hai, lekin domain ke liye Namecheap se campuscart.in Rs 650 mein kharida gaya tha. | #38 | ❌ | missing one of ["doesn't say", 'does not say', 'not in the chat', 'no information', 'not mentioned', "isn't mentioned", 'not stated', 'no total', 'not specified', 'only'] |
| 16 | Is Kabir coming to the Saturday meeting? | answered | Kabir is not attending the team meeting in person due to a family function, but he stated that he will join on a call. | #96 | ✅ |  |
| 17 | Did Aarav confirm he is attending the Saturday meeting? | answered | Yes, Aarav confirmed he is attending the Saturday meeting. | #92, #100, #102 | ✅ |  |
| 18 | Priya abhi kis cheez pe kaam kar rahi hai? | answered | Priya abhi seller dashboard pe kaam kar rahi hai, aur usne pehle listing page aur filters complete kar liye the. | #58 | ✅ |  |
