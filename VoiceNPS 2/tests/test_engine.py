"""Engine-level tests (stdlib only): python -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.mock import ConsoleOtpDelivery, MockBank, MockBillers
from app.dialog import DialogEngine, Session
from app.nlu import RuleNLU
from app.otp import OtpService


class Base(unittest.TestCase):
    def setUp(self):
        self.bank = MockBank()
        self.e = DialogEngine(RuleNLU(), self.bank, MockBillers(), OtpService(ConsoleOtpDelivery()))
        self.s = Session("user1")
        ConsoleOtpDelivery.last.pop("user1", None)
        self.seen = []
        orig = self.e.nlu.parse
        self.e.nlu.parse = lambda t, x=None: (self.seen.append(t), orig(t, x))[1]

    def say(self, t):
        return self.e.handle_voice(self.s, t)

    def otp(self, c):
        return self.e.handle_otp(self.s, c)

    def bad(self):
        c = ConsoleOtpDelivery.last["user1"]
        return "000000" if c != "000000" else "111111"


class Flows(Base):
    def test_small_transfer_no_otp(self):
        r = self.say("send 300 rupees to account 1 2 3 4 5 6 7 8 9 0 1 2 3")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Ramesh S.", r.speech)
        r = self.say("yes")
        self.assertTrue(r.done); self.assertIn("successful", r.speech)
        self.assertEqual(self.bank.balance_for_tests("user1"), 49700)
        self.assertNotIn("user1", ConsoleOtpDelivery.last)       # no OTP generated

    def test_large_transfer_otp_typed_only(self):
        self.say("transfer 2000 rupees to account 1234567890123")
        r = self.say("yes")
        self.assertEqual((r.state, r.expect), ("AWAIT_OTP", "otp_text"))
        code = ConsoleOtpDelivery.last["user1"]
        r = self.say(" ".join(code))                              # speaking the OTP must not work
        self.assertEqual(r.state, "AWAIT_OTP")
        self.assertEqual(self.bank.balance_for_tests("user1"), 50000)
        self.assertEqual(self.otp(self.bad()).state, "AWAIT_OTP")
        r = self.otp(code)
        self.assertTrue(r.done); self.assertEqual(self.bank.balance_for_tests("user1"), 48000)

    def test_threshold_boundary(self):
        self.say("send 499 rupees to account 1234567890123")
        self.assertTrue(self.say("yes").done)
        self.s = Session("user1")
        self.say("send 500 rupees to account 1234567890123")
        self.assertEqual(self.say("yes").state, "AWAIT_OTP")

    def test_invalid_account_flow(self):
        self.assertEqual(self.say("send 1000 rupees to account 1111111111111").state, "ASK_ACCOUNT")
        self.assertEqual(self.say("account 2222222222222").state, "CHOICE")
        self.assertEqual(self.say("try again").state, "ASK_ACCOUNT")
        r = self.say("9876543210987")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Sita K.", r.speech)
        self.assertTrue(self.say("cancel").done)

    def test_choice_cancel(self):
        self.say("send 1000 rupees to account 1111111111111"); self.say("2222222222222")
        self.assertTrue(self.say("terminate").done)

    def test_missing_amount_words(self):
        self.assertEqual(self.say("send money to 1234567890123").state, "ASK_AMOUNT")
        r = self.say("two thousand five hundred")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("2500", r.speech)

    def test_lakh(self):
        self.say("send money to 1234567890123")
        self.assertIn("100000", self.say("one lakh").speech)

    def test_electricity_bill(self):
        self.assertEqual(self.say("pay my electricity bill").state, "ASK_CUSTOMER")
        r = self.say("three zero one two four five")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("1840", r.speech)
        self.assertEqual(self.say("yes").state, "AWAIT_OTP")
        self.assertTrue(self.otp(ConsoleOtpDelivery.last["user1"]).done)

    def test_small_bill_no_otp(self):
        self.say("pay water bill"); self.say("1 1 2 2 3 3")
        self.assertTrue(self.say("yes").done)

    def test_bill_all_in_one_sentence_unknown_customer(self):
        self.say("pay internet bill")
        self.assertEqual(self.say("9 9 9 9 9 9").state, "ASK_CUSTOMER")

    def test_otp_lockout(self):
        self.say("send 900 rupees to 1234567890123"); self.say("yes")
        for _ in range(3):
            r = self.otp(self.bad())
        self.assertTrue(r.done); self.assertEqual(self.s.state, "CONTINUE")
        self.assertEqual(self.bank.balance_for_tests("user1"), 50000)

    def test_no_double_spend_on_replay(self):
        self.say("send 300 rupees to 1234567890123"); self.say("yes")
        key = None
        r1 = self.bank.transfer("user1", "1234567890123", 300, "k"); r2 = self.bank.transfer("user1", "1234567890123", 300, "k")
        self.assertEqual(r1.reference, r2.reference)

    def test_insufficient_funds(self):
        self.say("send 90000 rupees to 1234567890123"); self.say("yes")
        r = self.otp(ConsoleOtpDelivery.last["user1"])
        self.assertIn("balance", r.speech); self.assertEqual(self.bank.balance_for_tests("user1"), 50000)

    def test_limit_enforced(self):
        r = self.say("send 200000 rupees to 1234567890123")
        self.assertEqual(r.state, "ASK_AMOUNT")

    def test_cannot_send_to_self(self):
        self.assertEqual(self.say("send 100 rupees to 0011223344556").state, "ASK_ACCOUNT")

    def test_nlu_never_sees_private_data(self):
        self.say("send 900 rupees to 1234567890123"); self.say("yes")
        code = ConsoleOtpDelivery.last["user1"]
        self.otp(code)
        for t in self.seen:
            self.assertNotIn("Ramesh", t); self.assertNotIn(code, t)


class NamesAndCurrency(Base):
    def test_unique_name_with_rs_prefix(self):
        r = self.say("Send Rs.2000 to Sita")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Sita Koirala", r.speech); self.assertIn("2000", r.speech)

    def test_ambiguous_ramesh_asks_which(self):
        r = self.say("Send Rs.2000 to Ramesh")
        self.assertEqual(r.state, "DISAMBIGUATE")
        self.assertIn("Ramesh Sharma", r.speech); self.assertIn("Ramesh Bhattarai", r.speech)
        r = self.say("the second one")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Ramesh Bhattarai", r.speech)

    def test_disambiguate_by_surname(self):
        self.say("send 2000 rupees to Ramesh")
        r = self.say("Sharma")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Ramesh Sharma", r.speech)

    def test_full_name_goes_straight_through(self):
        r = self.say("Send Rs.2000 to Ramesh Bhattarai")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Ramesh Bhattarai", r.speech)

    def test_typo_in_verb_and_name(self):
        r = self.say("Sedn Rs.2000 to Rameesh Bhatarai")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Ramesh Bhattarai", r.speech)

    def test_missing_currency_asks_rupees(self):
        r = self.say("Send 2000 to Sita")
        self.assertEqual(r.state, "CONFIRM_CURRENCY"); self.assertIn("rupees", r.speech)
        r = self.say("yes")
        self.assertEqual(r.state, "CONFIRM")

    def test_currency_no_reasks_amount(self):
        self.say("Send 2000 to Sita")
        r = self.say("no")
        self.assertEqual(r.state, "ASK_AMOUNT")
        self.assertEqual(self.say("five hundred").state, "CONFIRM")   # answering 'how many rupees' fixes currency

    def test_missing_amount_and_recipient(self):
        self.assertEqual(self.say("I want to send money").state, "ASK_ACCOUNT")
        self.assertEqual(self.say("Sita Koirala").state, "ASK_AMOUNT")
        self.assertEqual(self.say("three hundred").state, "CONFIRM")

    def test_identical_names_are_told_apart(self):
        r = self.say("send Rs 500 to Hari")
        self.assertEqual(r.state, "DISAMBIGUATE")
        self.assertIn("Demo Bank", r.speech); self.assertIn("Sample Bank", r.speech)
        r = self.say("2")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Sample Bank", r.speech)

    def test_unknown_name_retries_then_choice(self):
        self.assertEqual(self.say("send Rs 500 to Gopal").state, "ASK_ACCOUNT")
        self.assertEqual(self.say("Krishna").state, "CHOICE")

    def test_word_amount_in_first_sentence(self):
        r = self.say("send two thousand rupees to Sita")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("2000", r.speech)

    def test_name_flow_still_needs_otp_over_500(self):
        self.say("send Rs.2000 to Sita"); r = self.say("yes")
        self.assertEqual(r.state, "AWAIT_OTP")


class SamePaymentWords(Base):
    """send / transfer / pay / remit / give all mean the same thing for people; bills are separate."""
    def test_all_verbs_transfer_to_person(self):
        for phrase in ["send Rs 300 to Sita", "transfer Rs 300 to Sita", "pay Rs 300 to Sita",
                       "pay Sita Rs 300", "give Sita 300 rupees", "remit 300 rupees to Sita",
                       "send Sita 300 rupees", "I want to pay Sita 300 rupees",
                       "can you please transfer three hundred rupees to Sita",
                       "Hey, send 300 rupees to Sita dai"]:
            self.s = Session("user1")
            r = self.say(phrase)
            self.assertEqual(r.state, "CONFIRM", phrase)
            self.assertIn("Sita Koirala", r.speech, phrase)
            self.assertIn("300", r.speech, phrase)

    def test_bill_phrases_go_to_bills(self):
        for phrase, state in [("pay my electricity bill", "ASK_CUSTOMER"), ("pay electricity", "ASK_CUSTOMER"),
                              ("pay internet bill", "ASK_CUSTOMER"), ("send money for water bill", "ASK_CUSTOMER"),
                              ("recharge my mobile", "ASK_CUSTOMER"), ("pay bill", "ASK_BILLER"),
                              ("I want to pay the wifi bill", "ASK_CUSTOMER")]:
            self.s = Session("user1")
            self.assertEqual(self.say(phrase).state, state, phrase)

    def test_pay_ramesh_is_a_transfer_not_a_bill(self):
        self.assertEqual(self.say("pay Ramesh 500 rupees").state, "DISAMBIGUATE")

    def test_whisper_style_numbers_with_commas(self):
        r = self.say("Send Rs. 1,000 to account 1,234,567,890,123.")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("1000", r.speech); self.assertIn("Ramesh S.", r.speech)

    def test_spoken_digits_after_i_want_to(self):
        r = self.say("I want to send 500 rupees to account one two three four five six seven eight nine zero one two three")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("Ramesh S.", r.speech)

    def test_topup_amount_in_sentence(self):
        self.say("recharge my mobile with 200 rupees")
        r = self.say("9 8 4 1 0 0 0 0 0 0")
        self.assertEqual(r.state, "CONFIRM"); self.assertIn("200", r.speech)


class ContinueOrEnd(Base):
    """After every transaction the assistant asks: another transaction, or end?"""
    def pay_small(self):
        self.say("send Rs 300 to Sita")
        return self.say("yes")

    def test_asks_after_payment(self):
        r = self.pay_small()
        self.assertTrue(r.done); self.assertEqual(r.state, "CONTINUE"); self.assertFalse(r.end)
        self.assertIn("another transaction, or end", r.speech); self.assertEqual(r.expect, "voice")

    def test_yes_continues(self):
        self.pay_small()
        r = self.say("yes")
        self.assertEqual(r.state, "IDLE"); self.assertFalse(r.end)
        self.assertEqual(self.say("send Rs 200 to Sita").state, "CONFIRM")

    def test_end_words_switch_the_session_off(self):
        for word in ["end", "no", "stop", "that's all", "thank you", "goodbye", "I am done", "cancel"]:
            self.s = Session("user1"); self.pay_small()
            r = self.say(word)
            self.assertTrue(r.end, word); self.assertEqual(r.state, "IDLE", word)
            self.assertEqual(r.expect, "none", word); self.assertIn("Goodbye", r.speech, word)

    def test_say_next_payment_directly(self):
        self.pay_small()
        r = self.say("send Rs 100 to Sita")
        self.assertEqual(r.state, "CONFIRM"); self.assertFalse(r.end)

    def test_another_and_continue_words(self):
        for word in ["another one", "one more", "continue", "yes please", "okay"]:
            self.s = Session("user1"); self.pay_small()
            self.assertFalse(self.say(word).end, word)

    def test_unclear_answer_asks_again(self):
        self.pay_small()
        r = self.say("banana")
        self.assertEqual(r.state, "CONTINUE"); self.assertFalse(r.end)

    def test_cancel_mid_payment_then_asks(self):
        self.say("send Rs 900 to Sita")
        r = self.say("cancel")
        self.assertEqual(r.state, "CONTINUE"); self.assertTrue(r.done); self.assertIn("cancelled", r.speech)
        self.assertTrue(self.say("end").end)

    def test_failed_payment_also_asks(self):
        self.say("send 90000 rupees to Sita"); self.say("yes")
        r = self.otp(ConsoleOtpDelivery.last["user1"])
        self.assertIn("balance", r.speech); self.assertEqual(r.state, "CONTINUE")

    def test_bye_ends_anywhere_even_mid_payment_and_clears_otp(self):
        self.say("send Rs 900 to Sita"); self.say("yes")
        self.assertEqual(self.s.state, "AWAIT_OTP")
        r = self.say("goodbye")
        self.assertTrue(r.end); self.assertEqual(self.s.state, "IDLE")
        self.assertEqual(self.otp("123456").speech, "No code is needed right now.")

    def test_stop_at_start_ends(self):
        self.assertTrue(self.say("stop").end)

    def test_new_session_after_end_works(self):
        self.pay_small(); self.assertTrue(self.say("end").end)
        self.assertEqual(self.say("send Rs 100 to Sita").state, "CONFIRM")


class NepaliReplies(Base):
    """lang='ne': every spoken sentence is Nepali (Devanagari), numbers and names included."""
    LATIN = __import__("re").compile(r"[A-Za-z]")

    def setUp(self):
        super().setUp()
        self.s = Session("user1", lang="ne")

    def check(self, r):
        self.assertFalse(self.LATIN.search(r.speech), r.speech)
        self.assertTrue(any("\u0900" <= ch <= "\u097f" for ch in r.speech), r.speech)
        return r

    def test_greeting_and_help(self):
        self.check(self.e.greeting("ne"))
        self.check(self.say("hello"))

    def test_full_transfer_flow_in_nepali(self):
        r = self.check(self.say("send Rs 2000 to Sita"))
        self.assertIn("सीता कोइराला", r.speech); self.assertIn("दुई हजार रुपैयाँ", r.speech)
        self.assertIn("स्याम्पल बैंक", r.speech); self.assertIn("शून्य नौ आठ सात", r.speech)
        r = self.check(self.say("yes")); self.assertEqual(r.state, "AWAIT_OTP")
        r = self.check(self.otp(ConsoleOtpDelivery.last["user1"]))
        self.assertIn("सफल", r.speech); self.assertIn("अन्त्य", r.speech); self.assertEqual(r.state, "CONTINUE")
        r = self.check(self.say("end")); self.assertTrue(r.end); self.assertIn("धन्यवाद", r.speech)

    def test_all_questions_in_nepali(self):
        for phrase in ["send money", "send Rs 500 to Ramesh", "send 700 to Sita", "pay bill", "recharge my mobile",
                       "send Rs 500 to Gopal", "send Rs 500 to Himal", "send Rs 500 to account 1111111111111"]:
            self.s = Session("user1", lang="ne")
            self.check(self.say(phrase))

    def test_ambiguous_names_listed_in_nepali(self):
        r = self.check(self.say("send Rs 1000 to Ramesh"))
        self.assertIn("रमेश शर्मा", r.speech); self.assertIn("रमेश भट्टराई", r.speech)
        r = self.check(self.say("second")); self.assertIn("रमेश भट्टराई", r.speech)

    def test_identical_names_get_bank_details_in_nepali(self):
        r = self.check(self.say("send Rs 500 to Hari"))
        self.assertIn("डेमो बैंक", r.speech); self.assertIn("स्याम्पल बैंक", r.speech)

    def test_bill_in_nepali(self):
        self.check(self.say("pay my electricity bill"))
        r = self.check(self.say("3 0 1 2 4 5"))
        self.assertIn("बिजुली", r.speech); self.assertIn("एक हजार आठ सय चालीस रुपैयाँ", r.speech)
        self.assertEqual(self.check(self.say("yes")).state, "AWAIT_OTP")
        self.check(self.say("1 2 3"))                                     # speaking the code is refused, in Nepali
        self.check(self.otp("000000" if ConsoleOtpDelivery.last["user1"] != "000000" else "111111"))

    def test_account_number_flow_names_are_first_name_only(self):
        r = self.check(self.say("send Rs 300 to account 1234567890123"))
        self.assertIn("रमेश", r.speech); self.assertNotIn("शर्मा", r.speech)

    def test_language_can_switch_mid_session(self):
        self.s.lang = "en"
        self.assertIn("Send", self.say("send Rs 300 to Sita").speech)
        self.s.lang = "ne"
        self.check(self.say("yes"))


if __name__ == "__main__":
    unittest.main()
