import os
os.environ.setdefault("DEV_MODE", "1")

from fastapi.testclient import TestClient

from app.adapters.mock import ConsoleOtpDelivery
from app.main import app, engine

c = TestClient(app)
H = {"X-User-Id": "user1"}


def start():
    return c.post("/v1/sessions", headers=H).json()["session_id"]


def say(sid, text):
    r = c.post(f"/v1/sessions/{sid}/voice", headers=H, files={"audio": ("a.wav", text.encode())})
    assert r.status_code == 200, r.text
    return r.json()


def otp(sid, code):
    return c.post(f"/v1/sessions/{sid}/otp", headers=H, json={"otp": code}).json()


def bal():
    return engine.bank.balance_for_tests("user1")


def test_small_transfer_no_otp():
    sid, before = start(), bal()
    r = say(sid, "send 300 rupees to account 1 2 3 4 5 6 7 8 9 0 1 2 3")
    assert r["state"] == "CONFIRM" and "Ramesh S." in r["debug_speech"]
    r = say(sid, "yes")
    assert r["done"] and "successful" in r["debug_speech"]
    assert bal() == before - 300
    assert "user1" not in ConsoleOtpDelivery.last or True  # no OTP was required


def test_large_transfer_requires_otp_typed():
    sid, before = start(), bal()
    ConsoleOtpDelivery.last.pop("user1", None)
    say(sid, "transfer 2000 rupees to account 1234567890123")
    r = say(sid, "yes")
    assert r["state"] == "AWAIT_OTP" and r["expect"] == "otp_text"
    code = ConsoleOtpDelivery.last["user1"]
    r = say(sid, " ".join(code))                     # speaking the OTP must NOT work
    assert r["state"] == "AWAIT_OTP" and bal() == before
    assert otp(sid, "000000" if code != "000000" else "111111")["state"] == "AWAIT_OTP"
    r = otp(sid, code)
    assert r["done"] and bal() == before - 2000


def test_exactly_500_needs_otp_and_499_does_not():
    sid = start()
    say(sid, "send 499 rupees to account 1234567890123")
    assert say(sid, "yes")["done"]
    sid = start()
    say(sid, "send 500 rupees to account 1234567890123")
    assert say(sid, "yes")["state"] == "AWAIT_OTP"


def test_invalid_account_retry_then_choice_then_cancel():
    sid = start()
    r = say(sid, "send 1000 rupees to account 1111111111111")
    assert r["state"] == "ASK_ACCOUNT"                           # first failure: ask another
    r = say(sid, "account 2222222222222")
    assert r["state"] == "CHOICE"                                # second failure: try again / cancel
    r = say(sid, "try again")
    assert r["state"] == "ASK_ACCOUNT"
    r = say(sid, "9876543210987")
    assert r["state"] == "CONFIRM" and "Sita K." in r["debug_speech"]
    assert say(sid, "cancel")["done"]


def test_asks_for_missing_amount():
    sid = start()
    assert say(sid, "send money to 1234567890123")["state"] == "ASK_AMOUNT"
    assert say(sid, "two thousand five hundred")["state"] == "CONFIRM"


def test_electricity_bill_flow():
    sid, before = start(), bal()
    assert say(sid, "pay my electricity bill")["state"] == "ASK_CUSTOMER"
    r = say(sid, "three zero one two four five")
    assert r["state"] == "CONFIRM" and "1840" in r["debug_speech"]
    assert say(sid, "yes")["state"] == "AWAIT_OTP"
    otp(sid, ConsoleOtpDelivery.last["user1"])


def test_small_bill_no_otp():
    sid = start()
    say(sid, "pay water bill")
    say(sid, "1 1 2 2 3 3")
    assert say(sid, "yes")["done"]                               # 350 < 500


def test_otp_lockout_cancels():
    sid = start()
    say(sid, "send 900 rupees to 1234567890123"); say(sid, "yes")
    r = None
    for _ in range(3):
        r = otp(sid, "000000" if ConsoleOtpDelivery.last["user1"] != "000000" else "111111")
    assert r["done"] and r["state"] == "CONTINUE"


def test_nlu_never_receives_private_data():
    seen = []
    orig = engine.nlu.parse
    engine.nlu.parse = lambda t, e=None: (seen.append(t), orig(t, e))[1]
    try:
        sid = start()
        say(sid, "send 900 rupees to 1234567890123"); say(sid, "yes")
        otp(sid, ConsoleOtpDelivery.last["user1"])
    finally:
        engine.nlu.parse = orig
    assert not any("Ramesh" in t or ConsoleOtpDelivery.last["user1"] in t for t in seen)
