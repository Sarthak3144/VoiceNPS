"""FULL SPEECH DEMO: you talk, the assistant talks back, hands-free. Only the OTP is typed.

    python -m pip install faster-whisper sounddevice numpy      (Windows/Linux also: pyttsx3)
    python check_audio.py       # run this first: tests speaker, mic and speech recognition
    python voice_loop.py

Say "goodbye" to finish. Set SHOW_TRANSCRIPT=0 to hide the on-screen log of what was heard/said.
"""
import os
import re
from getpass import getpass

os.environ.setdefault("STT_ENGINE", "app.speech:WhisperSTT")

os.environ.setdefault("VOICENPS_CONSOLE_SMS", "1")      # fake SMS printed here

from app.audio_io import listen, speak  # noqa: E402
from app.dialog import Session  # noqa: E402
from app.wiring import GREETING, build_engine  # noqa: E402

SHOW = os.getenv("SHOW_TRANSCRIPT", "1") == "1"


def say(text: str):
    if SHOW:
        print("ASSISTANT:", text)
    speak(text)


def main():
    print("Loading speech model (first run downloads it)...")
    engine, stt, _, verifier = build_engine()
    s = Session(user_id="user1")
    say(GREETING)
    while True:
        audio = listen()
        if not audio:
            say("I did not hear anything. Please say it again.")
            continue
        if not verifier.verify(s.user_id, audio):
            say("Sorry, I could not recognise your voice.")
            continue
        text = stt.transcribe(audio)
        if SHOW:
            print("HEARD:", text)
        if not text.strip():
            say("Sorry, I could not understand. Please say it again.")
            continue
        reply = engine.handle_voice(s, text)
        say(reply.speech)
        while reply.expect == "otp_text":
            reply = engine.handle_otp(s, getpass("Type the OTP (hidden): ").strip())   # the ONLY typing
            say(reply.speech)
        if reply.end:
            break


if __name__ == "__main__":
    main()
