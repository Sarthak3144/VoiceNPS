"""OTP service. Lives entirely outside the AI/NLU layer: the NLU never sees an OTP, and the
dialog engine only learns 'valid / invalid' from here. The code is stored hashed."""
import hashlib
import hmac
import os
import secrets
import time

from . import config


class OtpService:
    def __init__(self, delivery):
        self.delivery = delivery
        self._store: dict[str, dict] = {}

    @staticmethod
    def required(amount: float) -> bool:
        """Business rule: OTP only for amounts >= threshold (default NPR 500)."""
        return amount >= config.OTP_THRESHOLD_NPR

    def issue(self, user_id: str) -> None:
        otp = "".join(secrets.choice("0123456789") for _ in range(config.OTP_LENGTH))
        salt = os.urandom(8)
        self._store[user_id] = {
            "salt": salt,
            "hash": hashlib.sha256(salt + otp.encode()).digest(),
            "exp": time.time() + config.OTP_TTL_SECONDS,
            "attempts": 0,
        }
        self.delivery.send(user_id, otp)   # SMS to the user's phone; not returned to the caller

    def verify(self, user_id: str, otp: str) -> str:
        """Returns 'ok' | 'invalid' | 'expired' | 'locked' | 'none'."""
        rec = self._store.get(user_id)
        if not rec:
            return "none"
        if time.time() > rec["exp"]:
            self._store.pop(user_id, None)
            return "expired"
        if rec["attempts"] >= config.OTP_MAX_ATTEMPTS:
            return "locked"
        rec["attempts"] += 1
        good = hmac.compare_digest(hashlib.sha256(rec["salt"] + otp.encode()).digest(), rec["hash"])
        if good:
            self._store.pop(user_id, None)   # single use
            return "ok"
        return "locked" if rec["attempts"] >= config.OTP_MAX_ATTEMPTS else "invalid"

    def clear(self, user_id: str) -> None:
        self._store.pop(user_id, None)
