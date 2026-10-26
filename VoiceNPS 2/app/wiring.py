"""Builds the engine from config. Kept separate from FastAPI so scripts can reuse it."""
import importlib

from . import config
from .dialog import DialogEngine
from .otp import OtpService
from .speech import AllowAllVerifier

from .messages import render

GREETING = render("en", "greeting")      # English greeting (Nepali: messages.render("ne", "greeting"))


def load(path: str):
    mod, cls = path.split(":")
    return getattr(importlib.import_module(mod), cls)()


def build_engine():
    bank, billers = load(config.BANK_ADAPTER), load(config.BILLER_ADAPTER)
    otp = OtpService(load(config.OTP_DELIVERY))
    return (DialogEngine(load(config.NLU_ENGINE), bank, billers, otp),
            load(config.STT_ENGINE), load(config.TTS_ENGINE), AllowAllVerifier())
