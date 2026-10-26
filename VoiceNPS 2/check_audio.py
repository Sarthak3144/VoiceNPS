"""Run this BEFORE the demo. It checks speaker, microphone, speech recognition and command parsing."""
import os
os.environ.setdefault("STT_ENGINE", "app.speech:WhisperSTT")

from app.audio_io import listen, speak
from app.nlu import RuleNLU
from app.wiring import load
from app import config

print("1) Speaker test: you should HEAR a sentence...")
speak("Hello. This is the speaker test. If you can hear me, the speaker works.")

print("2) Loading speech recognition (first run downloads the model, needs internet)...")
stt = load(config.STT_ENGINE)

print("3) Microphone test: after the beep-less pause, SAY: 'Send two thousand rupees to Ramesh'")
speak("Please say: send two thousand rupees to Ramesh.")
audio = listen()
if not audio:
    raise SystemExit("No speech detected: check microphone permission (System Settings > Privacy > Microphone "
                     "for Terminal / VS Code) and the input device.")
text = stt.transcribe(audio)
print("   Heard:", repr(text))
it = RuleNLU().parse(text)
print("   Understood as:", it.name, it.slots)
print("OK if it says transfer with amount 2000.0 and recipient_name 'ramesh'.")
