"""Tests the demo server API end to end (stdlib only): python -m unittest discover -s tests -v"""
import json
import os
import sys
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import server as demo_app  # noqa: E402


class DemoServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), demo_app.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

    def say(self, t):
        return self.call("/api/say", {"text": t})

    def test_page_and_state(self):
        with urllib.request.urlopen(self.base + "/") as r:
            self.assertIn(b"VoiceNPS", r.read())
        st = self.call("/api/state")
        self.assertIn("Ramesh Sharma", st["contacts"])

    def test_full_flow_with_otp_and_sms(self):
        g = self.call("/api/session", {})
        self.assertEqual(g["expect"], "voice")
        before = g["balance"]
        r = self.say("Send Rs.2000 to Ramesh")
        self.assertEqual(r["state"], "DISAMBIGUATE")
        self.assertEqual(r["intent"]["slots"]["recipient_name"], "ramesh")
        r = self.say("the second one")
        self.assertEqual(r["state"], "CONFIRM")
        r = self.say("yes")
        self.assertEqual((r["state"], r["expect"]), ("AWAIT_OTP", "otp_text"))
        self.assertIn("verification code", r["sms"])
        code = r["sms"].split("code is ")[1][:6]
        self.assertEqual(self.call("/api/otp", {"otp": "12"})["error"], "bad_format")
        r = self.call("/api/otp", {"otp": code})
        self.assertTrue(r["done"]); self.assertEqual(r["result"]["amount"], 2000); self.assertTrue(r["result"]["otp"])
        self.assertEqual(r["balance"], before - 2000)

    def test_small_payment_has_no_sms_or_otp(self):
        self.call("/api/session", {})
        self.say("Pay Sita Rs 300")
        r = self.say("yes")
        self.assertTrue(r["done"]); self.assertFalse(r["result"]["otp"]); self.assertNotIn("sms", r)

    def test_cancel_has_no_receipt(self):
        self.call("/api/session", {})
        self.say("send rs 900 to sita")
        r = self.say("cancel")
        self.assertTrue(r["done"]); self.assertNotIn("result", r)

    def test_rupee_symbol_and_commas_from_chrome(self):
        self.call("/api/session", {})
        r = self.say("Send ₹2,000 to Sita")
        self.assertEqual(r["state"], "CONFIRM")           # symbol counts as 'rupees', no extra question
        self.assertIn("2000", r["speech"])

    def test_phonetic_names(self):
        for phrase in ["send rs 500 to Seeta", "send rs 500 to Rameesh Bhatarai", "send rs 500 to Hari Thaapa"]:
            self.call("/api/session", {})
            r = self.say(phrase)
            self.assertIn(r["state"], ("CONFIRM", "DISAMBIGUATE"), phrase)

    def test_after_payment_asks_to_continue_then_end_turns_mic_off(self):
        self.call("/api/session", {})
        self.say("Pay Sita Rs 300")
        r = self.say("yes")
        self.assertTrue(r["done"]); self.assertFalse(r["end"]); self.assertEqual(r["expect"], "voice")
        self.assertIn("another transaction", r["speech"])
        r = self.say("end")
        self.assertTrue(r["end"]); self.assertEqual(r["expect"], "none")

    def test_continue_yes_keeps_listening(self):
        self.call("/api/session", {})
        self.say("Pay Sita Rs 300"); self.say("yes")
        r = self.say("yes")
        self.assertFalse(r["end"]); self.assertEqual(r["expect"], "voice"); self.assertEqual(r["state"], "IDLE")

    def test_nepali_session_replies_in_nepali_and_understands_nepali(self):
        g = self.call("/api/session", {"lang": "ne"})
        self.assertEqual(g["lang"], "ne")
        r = self.say("सीतालाई तीन सय रुपैयाँ पठाउ")
        self.assertEqual(r["state"], "CONFIRM")
        self.assertIn("सीता कोइराला", r["speech"]); self.assertIn("तीन सय", r["speech"])
        self.assertFalse(any("a" <= ch.lower() <= "z" for ch in r["speech"]))
        r = self.say("हो")
        self.assertTrue(r["done"]); self.assertIn("अर्को कारोबार", r["speech"])
        r = self.say("अन्त्य")
        self.assertTrue(r["end"])

    def test_language_switch_midway(self):
        self.call("/api/session", {})
        self.assertEqual(self.call("/api/lang", {"lang": "ne"})["lang"], "ne")
        r = self.say("send")
        self.assertTrue(any("\u0900" <= ch <= "\u097f" for ch in r["speech"]))
        self.assertEqual(self.call("/api/lang", {"lang": "xx"})["lang"], "ne")     # invalid ignored

    def test_ping_and_tts_errors_are_json(self):
        self.assertTrue(self.call("/api/ping", {})["ok"])
        self.assertGreater(demo_app.PING["last"], 0)
        self.assertEqual(self.call("/api/tts?lang=fr&text=hi")["error"], "bad_request")
        r = self.call("/api/tts?lang=ne&text=" + urllib.parse.quote("नमस्ते"))
        self.assertIn(r.get("error"), ("gtts_missing", "tts_failed"))               # no gTTS/internet in tests

    def test_otp_not_visible_to_ai(self):
        self.call("/api/session", {})
        seen = []
        orig = demo_app._orig_parse
        demo_app._orig_parse = lambda t, e=None: (seen.append(t), orig(t, e))[1]
        try:
            self.say("send rs 900 to sita"); r = self.say("yes")
            code = r["sms"].split("code is ")[1][:6]
            self.call("/api/otp", {"otp": code})
        finally:
            demo_app._orig_parse = orig
        self.assertFalse(any(code in t for t in seen))


if __name__ == "__main__":
    unittest.main()
