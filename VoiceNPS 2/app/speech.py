"""Speech layer: audio in -> transcript, reply -> audio. Swap engines through config.py."""
import io
import os
import tempfile
import wave


class DevSTT:
    """Dev/test only: treats the uploaded 'audio' bytes as already-transcribed UTF-8."""
    def transcribe(self, audio: bytes) -> str:
        return audio.decode("utf-8", errors="ignore")


class WhisperSTT:
    """Offline speech-to-text. pip install faster-whisper. Language 'ne' = Nepali, 'en' = English.
    Set WHISPER_LANG=None to auto-detect (handles Nepali/English code-switching reasonably)."""
    def __init__(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(os.getenv("WHISPER_MODEL", "small"), compute_type="int8")
        self.lang = os.getenv("WHISPER_LANG", "en")
        self.lang = None if self.lang == "None" else self.lang
        # A hint that nudges recognition toward our vocabulary and names. Edit via WHISPER_PROMPT.
        self.prompt = os.getenv("WHISPER_PROMPT",
                                "Send 2000 rupees to Ramesh Sharma. Transfer Rs. 500 to Sita Koirala. "
                                "Pay electricity bill. Internet, water, top up. Ramesh Bhattarai, Hari Thapa. "
                                "Yes. No. Cancel. Account number 1 2 3 4 5 6 7 8 9 0 1 2 3.")

    def transcribe(self, audio: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            f.write(audio); f.flush()
            segs, _ = self.model.transcribe(f.name, language=self.lang, vad_filter=True,
                                            initial_prompt=self.prompt)
            return " ".join(s.text for s in segs).strip()


class DevTTS:
    """Dev/test only: returns the sentence as bytes."""
    mime = "text/plain"
    def synthesize(self, text: str) -> bytes:
        return text.encode()


class Pyttsx3TTS:
    """Offline TTS. pip install pyttsx3 (needs espeak-ng on Linux). Produces WAV bytes."""
    mime = "audio/wav"
    def synthesize(self, text: str) -> bytes:
        import pyttsx3
        eng = pyttsx3.init()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        eng.save_to_file(text, path); eng.runAndWait()
        data = open(path, "rb").read(); os.remove(path)
        return data


class AllowAllVerifier:
    """Placeholder speaker check. Replace with SpeechBrainVerifier below for voice biometrics."""
    def verify(self, user_id: str, audio: bytes) -> bool:
        return True


class SpeechBrainVerifier:
    """Voice-print check (ECAPA-TDNN). pip install speechbrain torchaudio.
    Enrol: store embedding per user. Verify: cosine similarity > threshold (tune ~0.5-0.7).
    Treat as ONE factor: recordings can be replayed, so it never replaces the OTP."""
    def __init__(self, enrolled: dict | None = None, threshold: float = 0.6):
        from speechbrain.inference.speaker import EncoderClassifier
        self.model = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb")
        self.enrolled, self.threshold = enrolled or {}, threshold

    def _embed(self, audio: bytes):
        import torch, torchaudio
        wav, sr = torchaudio.load(io.BytesIO(audio))
        return self.model.encode_batch(torchaudio.functional.resample(wav, sr, 16000)).squeeze()

    def enrol(self, user_id: str, audio: bytes):
        self.enrolled[user_id] = self._embed(audio)

    def verify(self, user_id: str, audio: bytes) -> bool:
        import torch
        ref = self.enrolled.get(user_id)
        return ref is not None and torch.cosine_similarity(ref, self._embed(audio), dim=0).item() >= self.threshold
