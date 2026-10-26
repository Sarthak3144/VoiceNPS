"""Easiest way to try the logic: type what the user WOULD say, read what the assistant WOULD say.
No server, no microphone, no extra installs.

    python dev_cli.py

Type 'quit' to leave. The OTP is typed when asked (exactly as in the real system); the fake SMS
shows the code in this terminal as [SMS-GATEWAY].
"""
import os

os.environ.setdefault("VOICENPS_CONSOLE_SMS", "1")      # show the fake SMS in this terminal

from app.dialog import Session  # noqa: E402
from app.wiring import GREETING, build_engine  # noqa: E402


def main():
    engine, _, _, _ = build_engine()
    s = Session(user_id="user1")
    print("ASSISTANT:", GREETING)
    while True:
        said = input("YOU (voice): ").strip()
        if said.lower() in ("quit", "exit", "q"):
            break
        reply = engine.handle_voice(s, said)
        print("ASSISTANT:", reply.speech)
        if reply.end:
            break
        while reply.expect == "otp_text":
            reply = engine.handle_otp(s, input("OTP (typed): ").strip())
            print("ASSISTANT:", reply.speech)


if __name__ == "__main__":
    main()
