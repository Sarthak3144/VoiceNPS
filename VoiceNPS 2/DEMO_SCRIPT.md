# Demo script (say these out loud)

Run `python demo_app.py` and open http://localhost:8765 in Chrome (or `python voice_loop.py` for the terminal version). The assistant greets you; then speak after it finishes talking.
Speak naturally but slowly for names and digits. Only the OTP is typed (hidden prompt).
Say "goodbye" at any time to finish. Say "cancel" to abort a payment.

| # | Feature | You say | Assistant does |
|---|---|---|---|
| 1 | Transfer by name, unique | "Send Rs 2000 to Sita" | Confirms "Sita K., Sample Bank, account ending 0 9 8 7"; you say "yes"; OTP is typed (2000 ≥ 500) |
| 2 | Same-meaning verbs | "Transfer 300 rupees to Sita" / "Pay Sita 300 rupees" / "Give Sita 300 rupees" | All treated as a transfer; 300 < 500 so NO OTP |
| 3 | Same first name | "Send Rs 1000 to Ramesh" | "I found 2 contacts named ramesh. 1, Ramesh Sharma. 2, Ramesh Bhattarai. Which one?" |
| 4 | Answer which one | "The second one" / "Sharma" / "first" | Confirms the chosen person |
| 5 | Full name | "Send Rs 1500 to Ramesh Bhattarai" | Goes straight to confirmation |
| 6 | Identical names | "Send Rs 500 to Hari" | Two "Hari Thapa" told apart by bank and last 4 digits; say "second" |
| 7 | Missing currency | "Send 2000 to Sita" | "You said 2000. Is that in rupees?" → "yes" |
| 8 | Missing amount | "Send money to Sita" | "How many rupees would you like to send?" → "five hundred" |
| 9 | Missing recipient | "I want to send money" | "Who would you like to send money to?" → "Sita Koirala" → asks amount |
| 10 | By account number | "Send Rs 800 to account 1 2 3 4 5 6 7 8 9 0 1 2 3" | Validates, names "Ramesh S." |
| 11 | Wrong account | "Send Rs 800 to account 1 1 1 1 1 1 1 1 1 1 1 1 1" | "I could not verify that account. Please say another…" |
| 12 | Wrong twice | say another wrong number | "Do you want to try again, or cancel?" → "try again" or "cancel" |
| 13 | Unknown name | "Send Rs 500 to Gopal" | "I could not find a contact named gopal…" |
| 14 | Electricity bill | "Pay my electricity bill" → "3 0 1 2 4 5" | Reads amount due 1840 rupees; "yes"; OTP typed |
| 15 | Small bill, no OTP | "Pay water bill" → "1 1 2 2 3 3" | 350 rupees; "yes"; completes with no OTP |
| 16 | Internet bill | "Pay internet bill" → "7 8 1 2 3 4" | 1500 rupees; OTP |
| 17 | Mobile top-up | "Recharge my mobile with 200 rupees" → "9 8 4 1 0 0 0 0 0 0" | 200 rupees; no OTP |
| 18 | Change your mind | at the confirmation say "no" | Asks for recipient again |
| 19 | Cancel | "cancel" | "Okay, cancelled." |
| 20 | Speaking the OTP | (when asked for OTP) say digits aloud | Refuses: "Please type the code. Do not say it out loud." |

OTP rule: under 500 rupees → no OTP; 500 and above → OTP typed.
Demo data (fake): contacts and bills in `data/accounts.json` and `data/bills.json`.
The OTP appears in the terminal as `[SMS-GATEWAY] OTP for user1: ...` (stands in for an SMS).

## Nepali and continue/end (new)
1. Switch to नेपाली. Say: "सीतालाई तीन सय रुपैयाँ पठाउ" -> assistant confirms in Nepali -> "हो".
2. Assistant asks "के तपाईं अर्को कारोबार गर्न चाहनुहुन्छ, कि अन्त्य गर्ने?" -> "हो" keeps the mic on.
3. Do a bill: "बिजुली बिल तिर्नु" -> customer number "तीन शून्य एक दुई चार पाँच".
4. At the continue question say "अन्त्य" (or "end"): goodbye is spoken and the mic turns OFF.
