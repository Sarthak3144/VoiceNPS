"""Microphone in / speaker out for the local hands-free demo."""
import io
import subprocess
import sys
import wave

RATE, BLOCK = 16000, 1600            # 16 kHz, 0.1 s blocks
MAX_WAIT_BLOCKS = 100               # give up after 10 s of silence
MAX_BLOCKS = 250                    # at most 25 s of speech
END_SILENCE_BLOCKS = 9              # stop ~0.9 s after the user stops talking

_pyttsx = None


def speak(text: str):
    """macOS: built-in `say` (most reliable). Elsewhere: pyttsx3."""
    global _pyttsx
    if sys.platform == "darwin":
        subprocess.run(["say", text], check=False)
        return
    import pyttsx3
    _pyttsx = _pyttsx or pyttsx3.init()
    _pyttsx.say(text); _pyttsx.runAndWait()


def _rms(block) -> float:
    import numpy as np
    return float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))


def listen() -> bytes:
    """Record until the user stops talking. Returns WAV bytes (b'' if nobody spoke)."""
    import numpy as np
    import sounddevice as sd
    frames, quiet, started = [], 0, False
    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=BLOCK) as st:
        ambient = max(_rms(st.read(BLOCK)[0]) for _ in range(3))      # calibrate to the room
        threshold = max(250.0, ambient * 2.5)
        for i in range(MAX_BLOCKS):
            block, _ = st.read(BLOCK)
            loud = _rms(block) > threshold
            if loud:
                started, quiet = True, 0
            elif started:
                quiet += 1
            if started:
                frames.append(block.copy())
                if quiet >= END_SILENCE_BLOCKS:
                    break
            elif i >= MAX_WAIT_BLOCKS:
                return b""
            else:
                frames = (frames + [block.copy()])[-3:]               # keep a little lead-in
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(np.concatenate(frames).tobytes())
    return buf.getvalue()
