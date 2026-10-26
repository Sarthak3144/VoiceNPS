"""Mock back-ends for development and tests. Replace with real Nepal bank / NEA / ISP integrations."""
import json
import os
import pathlib
import uuid
from typing import Optional

from .base import AccountInfo, BillInfo, Contact, TxResult

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"


class MockBank:
    def __init__(self):
        d = json.loads((DATA / "accounts.json").read_text())
        self.accounts = {a["account_no"]: a for a in d["accounts"]}
        self.users = d["users"]            # user_id -> {account_no, balance}
        self._done: dict[str, TxResult] = {}

    def validate_account(self, account_no: str) -> Optional[AccountInfo]:
        a = self.accounts.get(account_no)
        return AccountInfo(a["account_no"], a["holder_name"], a["bank"], a.get("name_ne", "")) if a else None

    def source_account(self, user_id: str) -> Optional[AccountInfo]:
        u = self.users.get(user_id)
        return self.validate_account(u["account_no"]) if u else None

    def contacts(self, user_id) -> list[Contact]:
        u = self.users.get(user_id, {})
        return [Contact(c["name"], c["account_no"], self.accounts.get(c["account_no"], {}).get("bank", ""),
                        c.get("name_ne", "")) for c in u.get("contacts", [])]

    def transfer(self, user_id, to_account, amount, idem_key) -> TxResult:
        if idem_key in self._done:           # idempotent: never double-spend on retry
            return self._done[idem_key]
        u = self.users.get(user_id)
        if not u or to_account not in self.accounts:
            r = TxResult(False, reason="invalid_account")
        elif u["balance"] < amount:
            r = TxResult(False, reason="insufficient_funds")
        else:
            u["balance"] -= amount
            r = TxResult(True, reference="TX" + uuid.uuid4().hex[:10].upper())
        self._done[idem_key] = r
        return r

    def balance_for_tests(self, user_id):
        return self.users[user_id]["balance"]


class MockBillers:
    def __init__(self):
        self.bills = json.loads((DATA / "bills.json").read_text())
        self._done: dict[str, TxResult] = {}

    def list_billers(self):
        return sorted({b["biller"] for b in self.bills})

    def lookup_bill(self, biller, customer_id) -> Optional[BillInfo]:
        for b in self.bills:
            if b["biller"] == biller and b["customer_id"] == customer_id:
                return BillInfo(biller, customer_id, b["customer_name"], b["amount_due"], b.get("name_ne", ""))
        return None

    def pay_bill(self, user_id, biller, customer_id, amount, idem_key) -> TxResult:
        if idem_key in self._done:
            return self._done[idem_key]
        r = TxResult(True, reference="BP" + uuid.uuid4().hex[:10].upper())
        self._done[idem_key] = r
        return r


class ConsoleOtpDelivery:
    """Stand-in for an SMS gateway. The OTP goes to the USER's phone, never to the AI layer."""
    last = {}    # exposed only so tests can read what the 'SMS' contained
    inbox = {}   # the demo UI shows this as the user's phone; the AI layer never reads it

    def send(self, user_id, otp):
        ConsoleOtpDelivery.last[user_id] = otp
        ConsoleOtpDelivery.inbox.setdefault(user_id, []).append(
            f"VoiceNPS: your verification code is {otp}. Do not share it with anyone.")
        if os.getenv("VOICENPS_CONSOLE_SMS", "0") == "1":      # off in the app window; on for terminal demos
            print(f"[SMS-GATEWAY] OTP for {user_id}: {otp}")
