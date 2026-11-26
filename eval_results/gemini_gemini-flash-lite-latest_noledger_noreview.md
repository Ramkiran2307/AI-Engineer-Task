# Eval results: gemini:gemini-flash-lite-latest (ledger off, review off)

Auto-check: **17 / 18** passed.

| # | Question | Status | System answer | Cited | Auto | Problems |
|---|---|---|---|---|---|---|
| 1 | What payment method are we using for the demo? | answered | The group is using Razorpay in test mode for the demo. | #66, #62 | ✅ |  |
| 2 | Who is responsible for payments now, and did they finish it? | answered | Kabir is responsible for payments now. He integrated Razorpay in test mode, but the payments feature is not fully finished yet because the webhook is still pending. | #67, #86, #20, #62 | ✅ |  |
| 3 | When is demo day? | answered | Demo day is on Thursday, 26 November 2026. | #79, #80 | ✅ |  |
| 4 | When is the report due? | answered | The report is due on 23 November 2026, which is three days before the demo day scheduled for 26 November 2026. | #81, #79, #28 | ✅ |  |
| 5 | Who is working on the search feature? | answered | Currently, nobody is working on the search feature, as it remains unassigned after Kabir gave it up. A discussion to decide who will take it is planned for the team meeting on Saturday, 14 Nov. | #44, #91, #87 | ✅ |  |
| 6 | Is there anything nobody is working on? | answered | Yes, search is currently unassigned. After Kabir gave it up, Priya, Rohan, and Meera declined or were busy, and Aarav proposed discussing it at the upcoming Saturday meeting. | #87, #97, #44 | ✅ |  |
| 7 | Who owns auth, and is it done? | answered | Kabir owns the auth module now, and it is done and merged. | #85, #54, #17 | ✅ |  |
| 8 | Rohan ne tests complete kar diye kya? | answered | Nahi, Rohan ke tests abhi complete nahi hue hain. Usne pehle promise kiya tha ki Sunday tak kar dega, aur last message tak uske tests pending hi hain. | #84, #91 | ✅ |  |
| 9 | Which domain did we buy, from where, and how much did it cost? | answered | The team bought the domain campuscart.in from Namecheap for Rs 650. | #38, #40 | ✅ |  |
| 10 | Where are we deploying, and is the app live yet? | answered | The team is deploying on Render, but the app is not live yet; Aarav plans to have it ready by November 15. | #83, #61 | ❌ | missing one of ["doesn't say", 'does not say', 'not known', 'unknown', 'no confirmation', 'not confirmed', 'not mention', 'no information', 'not stated', 'unclear', "isn't clear", 'not clear', 'no update', 'planned', 'target', 'by 15 nov'] |
| 11 | What did the team decide about search at the Saturday 14 Nov meeting? | not_in_chat | The chat doesn't say what the team decided about search at the Saturday 14 Nov meeting, because the meeting is only planned for Saturday 14 Nov and the chat ends on Thursday 12 Nov before it takes place. | #92, #97 | ✅ |  |
| 12 | Which logo did we finalise? | not_in_chat | The chat doesn't say which logo was finalized. Priya shared two logo options, and Meera expressed a preference for the second (blue) one, but no final decision was made before the chat ended. | #98, #101 | ✅ |  |
| 13 | Backend aur database ke liye kya decide hua tha? | answered | Backend ke liye Django aur database ke liye Postgres decide hua tha. | #12, #15 | ✅ |  |
| 14 | What is Meera responsible for now? | answered | Meera is responsible for the project report and PowerPoint presentation. | #68, #67 | ✅ |  |
| 15 | What is the total budget of the project? | not_in_chat | The chat doesn't say the total budget of the project. It only mentions that the domain (campuscart.in) cost Rs 650 on Namecheap. | #38 | ✅ |  |
| 16 | Is Kabir coming to the Saturday meeting? | answered | No, Kabir cannot attend the Saturday meeting in person because of a family function, but he plans to join via call. | #96 | ✅ |  |
| 17 | Did Aarav confirm he is attending the Saturday meeting? | answered | Yes, Aarav confirmed he is attending the Saturday meeting. | #92, #102 | ✅ |  |
| 18 | Priya abhi kis cheez pe kaam kar rahi hai? | answered | Priya abhi seller dashboard par kaam kar rahi hai. | #58, #89 | ✅ |  |
