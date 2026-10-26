"""FastAPI backend. Run: uvicorn app.main:app --reload"""
import base64
import os
import uuid

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from . import config
from .dialog import Reply, Session
from .wiring import GREETING, build_engine


app = FastAPI(title="VoiceNPS backend")
engine, stt, tts, verifier = build_engine()
SESSIONS: dict[str, Session] = {}      # production: Redis with TTL
DEV_MODE = os.getenv("DEV_MODE", "0") == "1"   # dev only: also return the spoken sentence as text


def _user(x_user_id: str | None) -> str:
    # Production: validate the app's JWT / session token here and derive the user id from it.
    if not x_user_id:
        raise HTTPException(401, "missing user")
    return x_user_id


def _get(sid: str, user: str) -> Session:
    s = SESSIONS.get(sid)
    if not s or s.user_id != user:
        raise HTTPException(404, "no such session")
    return s


def _pack(reply) -> dict:
    audio = tts.synthesize(reply.speech)
    out = {"state": reply.state, "expect": reply.expect, "done": reply.done, "end": reply.end,
           "listen_next": reply.expect == "voice",   # client reopens the mic automatically
           "audio_b64": base64.b64encode(audio).decode(), "audio_mime": tts.mime}
    if DEV_MODE:
        out["debug_speech"] = reply.speech
    return out


@app.post("/v1/sessions")
def new_session(x_user_id: str | None = Header(None)):
    user = _user(x_user_id)
    sid = uuid.uuid4().hex
    SESSIONS[sid] = Session(user_id=user)
    # The assistant speaks first, so the whole interaction is hands-free.
    return {"session_id": sid, **_pack(Reply(GREETING, "IDLE", "voice"))}


@app.post("/v1/sessions/{sid}/voice")
async def voice(sid: str, audio: UploadFile = File(...), x_user_id: str | None = Header(None)):
    s = _get(sid, _user(x_user_id))
    data = await audio.read()
    if not verifier.verify(s.user_id, data):
        raise HTTPException(403, "voice not recognised")
    return _pack(engine.handle_voice(s, stt.transcribe(data)))


class OtpIn(BaseModel):
    otp: str


@app.post("/v1/sessions/{sid}/otp")
def otp(sid: str, body: OtpIn, x_user_id: str | None = Header(None)):
    """The ONLY text input in the system. Goes straight to the OTP service; the NLU never sees it."""
    s = _get(sid, _user(x_user_id))
    if not body.otp.isdigit() or len(body.otp) != config.OTP_LENGTH:
        raise HTTPException(422, "bad otp format")
    return _pack(engine.handle_otp(s, body.otp))


class SayIn(BaseModel):
    text: str


if DEV_MODE:
    @app.post("/v1/dev/sessions/{sid}/say")
    def dev_say(sid: str, body: SayIn, x_user_id: str | None = Header(None)):
        """DEV ONLY (DEV_MODE=1): type what the user would say; get back what the assistant would say.
        Easier than uploading a file in the /docs page. Not mounted when DEV_MODE is off."""
        s = _get(sid, _user(x_user_id))
        r = engine.handle_voice(s, body.text)
        return {"assistant_says": r.speech, "state": r.state, "expect": r.expect, "done": r.done}
