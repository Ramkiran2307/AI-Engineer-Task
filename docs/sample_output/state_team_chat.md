# State of the project — team_chat.txt

**Project:** CampusCart  

_As of the last message: Thu 12 Nov 2026 20:13. Nothing after that is known._

## Current decisions

- **Project Idea:** CampusCart - marketplace for college students to buy and sell used books, cycles etc — _[#7 03 Oct Meera; #6 03 Oct Rohan; #5 03 Oct Priya; #4 03 Oct Aarav]_
- **Tech Stack:** Django backend, React frontend, Postgres database — _[#15 03 Oct Aarav; #14 03 Oct Rohan; #13 03 Oct Meera; #12 03 Oct Aarav +4 earlier]_
    - earlier: React + Firebase
    - earlier: Django + React + SQLite
- **Domain:** Bought campuscart.in from Namecheap for Rs 650 — _[#40 16 Oct Aarav; #39 16 Oct Priya; #38 16 Oct Aarav; #37 16 Oct Kabir +2 earlier]_
- **Payments Integration:** Razorpay test mode (no KYC required) — _[#66 02 Nov Aarav; #65 02 Nov Priya; #64 02 Nov Meera; #63 02 Nov Aarav +6 earlier]_
    - earlier: Razorpay with live mode (dropped due to lack of business KYC)
    - earlier: UPI QR code with manual confirmation
- **Deployment Platform:** Render — _[#61 26 Oct Aarav; #60 26 Oct Meera; #59 26 Oct Aarav]_
    - earlier: AWS (dropped due to billing concerns on free tier)

## Who owns what

| Workstream | Owner | Status | Detail | Source |
|---|---|---|---|---|
| Auth (Login/Signup) | Kabir | done | Auth is done and merged. | _[#85 10 Nov Kabir; #54 24 Oct Kabir; #53 24 Oct Kabir; #52 24 Oct Rohan +2 earlier]_ |
| Listings UI & Seller Dashboard | Priya | in progress | Listing page and filters done; currently working on seller dashboard. | _[#58 26 Oct Priya; #46 19 Oct Priya; #26 09 Oct Rohan; #25 09 Oct Priya +4 earlier]_ |
| Report and PPT | Meera | in progress | Took over report and PPT fully after payment tasks shifted to Kabir. | _[#68 02 Nov Meera; #28 12 Oct Meera; #20 05 Oct Meera; #17 05 Oct Aarav]_ |
| Chat & Payments | Kabir | in progress | Chat is at 70%; payments checkout integrated using Razorpay test mode, webhook remaining. | _[#86 10 Nov Kabir; #85 10 Nov Kabir; #67 02 Nov Kabir; #62 02 Nov Kabir +4 earlier]_ |
| Deployment | Aarav | in progress | Committed to having deployment ready on Render by 15 Nov. | _[#83 09 Nov Aarav; #17 05 Oct Aarav]_ |
| Database Schema & Tests | Rohan | in progress | Schema v2 ready with orders table; tests are pending and promised by this Sunday. | _[#91 10 Nov Rohan; #84 09 Nov Rohan; #78 07 Nov Rohan; #75 06 Nov Rohan +3 earlier]_ |

## Deadlines & dates

- **Report Deadline:** 23 Nov 2026 *(confirmed)* — _[#81 09 Nov Meera; #72 05 Nov Meera; #28 12 Oct Meera]_
    - earlier: 1 Dec 2026
    - earlier: 24 Nov 2026
- **Demo Day:** 26 Nov 2026 *(confirmed)* — _[#80 09 Nov Aarav; #79 09 Nov Priya; #69 05 Nov Aarav; #28 12 Oct Meera]_
    - earlier: 4 Dec 2026
    - earlier: 27 Nov 2026
- **Deployment Ready:** 15 Nov 2026 *(tentative)* — _[#83 09 Nov Aarav]_

## Unassigned (nobody is working on it)

- **Search Feature:** Dropped by Kabir due to chat complexity; currently unassigned and needs discussion. — _[#97 12 Nov Aarav; #91 10 Nov Rohan; #90 10 Nov Meera; #89 10 Nov Priya +5 earlier]_

## Still open / unresolved

- **Logo Selection:** Priya shared 2 logo options; Meera prefers the second blue one, awaiting group consensus. — _[#101 12 Nov Meera; #99 12 Nov Priya; #98 12 Nov Priya]_
- **Team Meeting:** Scheduled for Saturday 14 Nov 2026 at 4 PM at the college library (Kabir joining via call). — _[#97 12 Nov Aarav; #96 12 Nov Kabir; #95 12 Nov Rohan; #94 12 Nov Meera +2 earlier]_

