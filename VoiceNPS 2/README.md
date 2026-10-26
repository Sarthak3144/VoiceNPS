# VoiceNPS: voice-controlled payments (AI + backend)

## Run the app (one command, no web hosting)

```
pip install gTTS          # optional: natural Nepali voice (needs internet)
python demo_app.py        # or double-click VoiceNPS.command (Mac) / VoiceNPS.bat (Windows)
```

A VoiceNPS window opens (Chrome or Edge in app mode: no tabs, no address bar). The engine runs on this
computer only (127.0.0.1); nothing is hosted online. Close the window, or press Ctrl+C, and it stops.

- **Languages:** switch English / नेपाली at the bottom of the window. In Nepali the assistant listens
  for Nepali (ne-NP) and replies in Nepali for every step: transfer, bills, confirmation, OTP prompt,
  receipt, errors and the continue question. Amounts and names are spoken as Nepali words
  ("दुई हजार रुपैयाँ", "सीता कोइराला").
- **After every payment** the assistant asks: *"Would you like to make another transaction, or end?"*
  Say **yes** and the mic stays on. Say **end / no / goodbye** (अन्त्य / होइन / धन्यवाद) and the mic turns off;
  tap the mic to start again.
- **Nepali voice:** uses gTTS when installed and online; otherwise the browser's own Nepali (or Hindi) voice.
  If neither exists the reply is shown as text. Windows Chrome/Edge usually has a Hindi voice; macOS has none for Nepali, so install gTTS there.
- **OTP** (500 and above) is the only typed input; it never reaches the AI layer.
- Options: `python demo_app.py --port 9000 --browser "/path/to/chrome" --no-window`
- Terminal-only alternatives: `python dev_cli.py` (typing) and `python voice_loop.py` (real mic).
- Tests: `python -m unittest tests.test_engine tests.test_demo_server`

Layout: `app/dialog.py` (state machine), `app/nlu.py` (command understanding), `app/messages.py` (every sentence, en + ne),
`app/nepali.py` (Nepali numbers, names, speech clean-up), `app/phonetics.py` (name matching),
`app/adapters/` (plug your own bank/biller/SMS here), `app/server.py` (local engine), `ui/index.html` (the window).

## 0. Quickest way to try it (no server, no mic)

```bash
python dev_cli.py
```
Type what the user would say, read what the assistant would say. Try:
- `Send Rs.2000 to Ramesh` → "I found 2 contacts named ramesh… Which one?" → `second` → confirm → `yes` → OTP typed.
- `Send 2000 to Sita` → "Is that in rupees?" → `yes`.
- `Sedn Rs.500 to Rameesh Bhatarai` (typos are tolerated).
- `Send Rs 500 to Hari` (two identical names; it reads bank and last 4 digits to tell them apart).
- `pay electricity bill` → `301245`.

Demo contacts live in `data/accounts.json`: Ramesh Sharma, Ramesh Bhattarai, Sita Koirala, two Hari Thapa, Himalayan Traders.

## 1. Architecture

```
 Client app (not your job)            Backend (this project)
 ┌───────────────┐  audio   ┌──────────────────────────────────────────────┐
 │ mic / speaker │ ───────► │ 1 Speaker check (optional voice-print)       │
 │ OTP text box  │          │ 2 STT  audio → transcript                    │
 └───────────────┘          │ 3 NLU  transcript → intent  ◄── the "AI"     │
        ▲  audio reply      │ 4 Dialog engine (state machine, rules)       │
        └────────────────── │ 5 TTS  reply → audio                         │
        OTP text ─────────► │ OTP service ── SMS gateway ──► user's phone  │
                            │ Adapters: Bank | Billers | OTP delivery      │
                            └──────────────────────────────────────────────┘
```

Key security design:
- **The AI only classifies.** NLU gets the transcript and a slot hint. It never sees balances, full names, OTPs or account data, and it cannot call the bank. Only the dialog engine does, after the user says "yes".
- **OTP never goes through speech.** It is typed, goes to `/otp`, is verified by `OtpService` (hashed, 120 s expiry, 3 attempts, single use), and is delivered by SMS to the user's phone. If the user speaks digits during OTP, the system tells them to type it.
- **OTP rule:** amount `< 500` → no OTP generated. `>= 500` → OTP (set `OTP_THRESHOLD_NPR`). Exactly 500 needs an OTP.
- **Idempotency key** per confirmed payment prevents double-spend on retries.
- **Audit log** (`audit.log`) records masked events only.

## 2. Transfer flow 

```
"send 2000 to account 123…"
   → validate destination account (bank adapter)
        ├─ found → "Send 2000 rupees to Ramesh S., account ending 0 1 2 3. Say yes to confirm."
        │            ├─ yes → amount ≥ 500? ─ no → execute
        │            │                       └ yes → SMS OTP → user TYPES OTP → execute
        │            └─ no  → ask account again
        └─ not found (1st time) → "Please say another account number"
             └─ not found (2nd time) → "Try again, or cancel?"
                      ├─ try again → ask account    └─ cancel → end
```
Bills (electricity, internet, water, mobile top-up) use the same engine: biller → customer number → lookup (shows amount due) → confirm → OTP rule → pay.

### Names, missing values and look-alikes
- Recipient by **name** ("Send Rs.2000 to Ramesh Bhattarai"): the engine matches the spoken name against the user's saved contacts (typo-tolerant). The AI layer only extracts the spoken name; it never sees the contact list.
- Several matches → "I found 2 contacts named Ramesh… Which one?" The user answers "second", "the last one" or "Sharma". Identical names are told apart by bank and last 4 digits.
- Amount without a currency ("Send 2000 to Ramesh") → "You said 2000. Is that in rupees?"
- Missing recipient or amount → asked by voice. The destination account is still validated with the bank after a name is resolved, and the retry/cancel rules apply to unknown names too.

## 3. Dataset: what you need and don't need

- **No ML training is needed for the command set.** It is small and closed (transfer, pay bill, yes/no/cancel/retry, numbers), so `RuleNLU` handles it deterministically at zero cost.
- **STT:** use a pre-trained model (Whisper, `faster-whisper`). Nepali is supported (`WHISPER_LANG=ne`) but accuracy varies, so test with real Nepali speakers; cloud STT (Google/Azure) is an alternative if the employer allows audio leaving their servers.
- **To evaluate:** write 200+ example utterances per intent yourself (English, Nepali, mixed), record 5-10 volunteers, and measure word error rate and intent accuracy. Digit sequences and amounts ("दुई हजार पाँच सय") are the riskiest part.
- **Account/bill data:** comes from the employer's real systems through the adapters. `data/*.json` is fake demo data only.
- **Speaker verification:** needs a short enrolment recording per user. Treat it as one factor, never a replacement for the OTP.

## 4. Install and run

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_engine.py" -v   # 16 engine tests
pytest                                                         # also runs the API tests
uvicorn app.main:app --reload                                  # http://127.0.0.1:8000/docs
```

Easiest in the browser (http://127.0.0.1:8000/docs), with `DEV_MODE=1`: use `POST /v1/sessions`, then `POST /v1/dev/sessions/{sid}/say` with `{"text": "send Rs.2000 to Ramesh"}`, then `POST /v1/sessions/{sid}/otp`. Or with curl (the "audio" is plain text; DEV_MODE=1 also returns `debug_speech`):
```bash
SID=$(curl -s -X POST localhost:8000/v1/sessions -H "X-User-Id: user1" | python -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
echo "send 2000 to account 1234567890123" > a.txt
curl -s -X POST localhost:8000/v1/sessions/$SID/voice -H "X-User-Id: user1" -F audio=@a.txt
echo "yes" > a.txt && curl -s -X POST localhost:8000/v1/sessions/$SID/voice -H "X-User-Id: user1" -F audio=@a.txt
# the OTP is printed by the mock SMS gateway in the server console:
curl -s -X POST localhost:8000/v1/sessions/$SID/otp -H "X-User-Id: user1" -H "Content-Type: application/json" -d '{"otp":"123456"}'
```

## 5a. Fully voice, hands-free (what changed)

- The assistant speaks first: `POST /v1/sessions` returns a spoken greeting (`audio_b64`).
- Every reply is audio. `listen_next: true` tells the client to reopen the mic automatically, with no button. When `expect` is `otp_text`, the client shows the OTP box (the only typed input) and the voice prompt tells the user to type the code.
- Replies include the sentence as text only when `DEV_MODE=1` (off by default).
- Local hands-free demo with your mic and speaker (no client app needed): `python voice_loop.py` (install line is at the top of the file).

## 5. Real speech (switch from dev mode)

```bash
pip install faster-whisper pyttsx3      # Linux also: sudo apt install espeak-ng ffmpeg
export STT_ENGINE=app.speech:WhisperSTT TTS_ENGINE=app.speech:Pyttsx3TTS WHISPER_LANG=en DEV_MODE=0
```
Client sends WAV (16 kHz mono works best) to `/v1/sessions/{id}/voice`; response has `audio_b64` (WAV) to play. For better Nepali TTS, implement the same `synthesize(text) -> bytes` interface with a cloud TTS.

Optional LLM understanding: `pip install anthropic`, set `ANTHROPIC_API_KEY` and `NLU_ENGINE=app.nlu:LLMNLU`. Only the transcript is sent. Rules remain the fallback.

## 6. Making it flexible

Everything is swappable in `app/config.py` or by env var:

| Setting | Meaning |
|---|---|
| `BANK_ADAPTER` | class implementing `validate_account`, `source_account`, `transfer` |
| `BILLER_ADAPTER` | class implementing `list_billers`, `lookup_bill`, `pay_bill` |
| `OTP_DELIVERY` | class with `send(user_id, otp)` (their SMS gateway) |
| `OTP_THRESHOLD_NPR`, `MAX_SINGLE_TRANSFER_NPR`, `OTP_TTL_SECONDS`, `OTP_MAX_ATTEMPTS`, `MAX_ACCOUNT_RETRIES` | business rules |
| `STT_ENGINE`, `TTS_ENGINE`, `NLU_ENGINE` | speech/AI components |

To connect real systems, copy `app/adapters/mock.py`, replace the bodies with their API calls (keep the same method signatures, see `base.py`), and set `BANK_ADAPTER=mypackage.module:MyBank`. Ask your supervisor for their API specs (NCHL/connectIPS, Fonepay, NEA, ISP billers); I have not assumed any real API.

## 7. Before production (the honest checklist)

1. Authentication: replace `X-User-Id` with real token validation (JWT) in `main._user`.
2. Sessions: move `SESSIONS` to Redis with a TTL.
3. HTTPS only, rate limiting, per-user daily limits, device binding.
4. Never log transcripts or OTPs. Review `audit.log` retention with compliance.
5. Voice alone is spoofable (replay, cloning), so keep OTP/PIN for larger amounts and add anti-spoof checks.
6. Regulatory review (Nepal Rastra Bank payment rules) and pen-test before real money flows.
7. Test STT with real Nepali accents, background noise and digit strings.

## 8. Timeline

| Phase | Work | Time |
|---|---|---|
| 1 | Run this project, read the code, demo with dev mode | 1 h |
| 2 | Real STT/TTS, test with your own voice | 2-3 h |
| 3 | Adapters against employer's sandbox APIs | 1-3 days |
| 4 | Nepali utterances, accuracy testing | 2-3 days |
| 5 | Voice-print, auth, Redis, security review | 1-2 weeks |

## Files
`app/main.py` API · `app/wiring.py` engine setup · `voice_loop.py` hands-free mic demo · `app/dialog.py` state machine · `app/nlu.py` command understanding · `app/otp.py` OTP service · `app/speech.py` STT/TTS/speaker · `app/adapters/` bank/biller/SMS interfaces and mocks · `data/` demo data · `tests/` tests
