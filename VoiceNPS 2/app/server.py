"""VoiceNPS local engine. Standard library only (gTTS is optional, for the Nepali voice).

The app window talks to this small server on 127.0.0.1 (this computer only; nothing is hosted online).
The AI layer only ever receives the transcript of what the user said. The OTP is typed in the app and
never goes through the AI layer.
"""
import io
import json
import pathlib
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config
from .adapters.mock import ConsoleOtpDelivery
from .dialog import EXPECT, Reply, Session
from .nepali import normalize_transcript
from .wiring import build_engine

ROOT = pathlib.Path(__file__).resolve().parents[1]
USER = "user1"
LANGS = ("en", "ne")
engine, _, _, _ = build_engine()
LOCK = threading.Lock()
CTX = {"session": Session(USER), "history": [], "otp_used": False, "intent": None, "normalized": None}
PING = {"last": 0.0, "count": 0}              # the window's heartbeat: lets the launcher quit when it closes

_orig_parse = engine.nlu.parse


def _spy(transcript, expecting=None):          # records what the AI layer understood (for the side panel)
    intent = _orig_parse(transcript, expecting)
    shown = dict(intent.slots)
    if CTX.get("normalized"):
        shown["interpreted as"] = CTX["normalized"]
    CTX["intent"] = {"name": intent.name, "slots": shown, "expecting": expecting}
    return intent


engine.nlu.parse = _spy


def balance():
    f = getattr(engine.bank, "balance_for_tests", None)
    return f(USER) if f else None


def reply_payload(reply, heard=None):
    s = CTX["session"]
    p = {"speech": reply.speech, "state": reply.state, "expect": reply.expect, "done": reply.done,
         "end": reply.end, "lang": s.lang, "heard": heard, "intent": CTX["intent"], "balance": balance(),
         "otp_rule": f"OTP needed for amounts of NPR {config.OTP_THRESHOLD_NPR:.0f} and above"}
    if reply.state == "AWAIT_OTP":
        CTX["otp_used"] = True
        inbox = ConsoleOtpDelivery.inbox.get(USER, [])
        p["sms"] = inbox[-1] if inbox else None
    if reply.done:
        res = s.last_result
        if res and res.get("ok"):
            res = dict(res, otp=CTX["otp_used"])
            CTX["history"].insert(0, res)
            p["result"] = res
        CTX["otp_used"] = False
        s.last_result = None
    return p


def state_payload():
    me = engine.bank.source_account(USER)
    return {"account": f"{me.bank} ••{me.account_no[-4:]}", "holder": me.holder_name, "balance": balance(),
            "contacts": [c.name for c in engine.bank.contacts(USER)],
            "billers": engine.billers.list_billers(), "history": CTX["history"][:6],
            "otp_threshold": config.OTP_THRESHOLD_NPR, "otp_length": config.OTP_LENGTH,
            "lang": CTX["session"].lang}


# ---------------------------------------------------------------- Nepali voice (server side)
_TTS_CACHE: dict = {}


class TTSUnavailable(Exception):
    pass


def synthesize(lang: str, text: str) -> bytes:
    """Natural Nepali speech through gTTS (pip install gTTS; needs internet). The page falls back to
    the browser's own voices when this is unavailable."""
    key = (lang, text)
    if key in _TTS_CACHE:
        return _TTS_CACHE[key]
    try:
        from gtts import gTTS
    except ImportError as e:
        raise TTSUnavailable("gtts_missing") from e
    buf = io.BytesIO()
    gTTS(text=text, lang=lang).write_to_fp(buf)
    data = buf.getvalue()
    if len(_TTS_CACHE) > 400:
        _TTS_CACHE.clear()
    _TTS_CACHE[key] = data
    return data


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):               # keep the terminal clean
        pass

    def _send(self, code, data: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._send(200, (ROOT / "ui" / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/state":
            with LOCK:
                self._json(state_payload())
        elif url.path == "/api/tts":
            q = urllib.parse.parse_qs(url.query)
            lang, text = (q.get("lang") or ["ne"])[0], (q.get("text") or [""])[0].strip()
            if lang not in LANGS or not text or len(text) > 600:
                return self._json({"error": "bad_request"}, 400)
            try:
                self._send(200, synthesize(lang, text), "audio/mpeg")
            except TTSUnavailable as e:
                self._json({"error": str(e)}, 501)
            except Exception:                      # no internet, blocked, rate limited ...
                self._json({"error": "tts_failed"}, 502)
        else:
            self.send_response(204 if self.path == "/favicon.ico" else 404)
            self.end_headers()

    def do_POST(self):
        body = self._body()
        if self.path == "/api/ping":
            PING["last"], PING["count"] = time.time(), PING["count"] + 1
            return self._json({"ok": True})
        with LOCK:
            if self.path == "/api/session":
                lang = body.get("lang") if body.get("lang") in LANGS else "en"
                CTX["session"], CTX["otp_used"], CTX["intent"], CTX["normalized"] = Session(USER, lang=lang), False, None, None
                ConsoleOtpDelivery.inbox.clear()
                return self._json({**reply_payload(engine.greeting(lang)), "info": state_payload()})
            s = CTX["session"]
            if self.path == "/api/lang":
                if body.get("lang") in LANGS:
                    s.lang = body["lang"]
                return self._json({"lang": s.lang})
            if self.path == "/api/say":
                text = str(body.get("text", "")).strip()
                if not text:
                    return self._json({"error": "empty"}, 400)
                CTX["intent"] = None
                s.last_result = None
                said = normalize_transcript(text, EXPECT.get(s.state)) or text
                CTX["normalized"] = said if said != text else None
                return self._json(reply_payload(engine.handle_voice(s, said), heard=text))
            if self.path == "/api/otp":
                code = str(body.get("otp", "")).strip()
                if not (code.isdigit() and len(code) == config.OTP_LENGTH):
                    return self._json({"error": "bad_format"}, 400)
                CTX["intent"] = None
                s.last_result = None
                return self._json(reply_payload(engine.handle_otp(s, code)))
        self._json({"error": "not found"}, 404)


def make_server(port: int = 8765) -> ThreadingHTTPServer:
    try:
        return ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:                              # port busy: let the system pick a free one
        return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
