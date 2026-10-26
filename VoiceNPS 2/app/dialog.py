"""Deterministic dialog engine. The NLU only classifies; every money-moving decision is a
state transition here, and the user must say 'yes' (and type the OTP when required).

All sentences come from app/messages.py in the session's language (English or Nepali).
After every finished transaction the engine asks "another transaction, or end?" and, on "end",
returns a reply with end=True so the app can switch the microphone off."""
import json
import pathlib
import re
import time
import uuid
from dataclasses import dataclass, field

from . import config
from . import messages as M
from .phonetics import best_suggestion, phonetic_match

(IDLE, ASK_ACCOUNT, ASK_AMOUNT, ASK_BILLER, ASK_CUSTOMER, DISAMBIGUATE, CONFIRM_NAME,
 CONFIRM_CURRENCY, CONFIRM, CHOICE, AWAIT_OTP, CONTINUE) = (
    "IDLE", "ASK_ACCOUNT", "ASK_AMOUNT", "ASK_BILLER", "ASK_CUSTOMER", "DISAMBIGUATE", "CONFIRM_NAME",
    "CONFIRM_CURRENCY", "CONFIRM", "CHOICE", "AWAIT_OTP", "CONTINUE")

EXPECT = {IDLE: None, ASK_ACCOUNT: "recipient", ASK_AMOUNT: "amount", ASK_BILLER: "any",
          ASK_CUSTOMER: "customer_id", DISAMBIGUATE: "choice", CONFIRM_NAME: "yes_no",
          CONFIRM_CURRENCY: "yes_no", CONFIRM: "yes_no", CHOICE: "retry_cancel", AWAIT_OTP: None,
          CONTINUE: "yes_no"}

BYE_RE = re.compile(r"\b(goodbye|good bye|bye)\b")
FINISH_RE = re.compile(r"\b(thanks?|thank you|that'?s all|that is all|nothing|nothing else|done|finish(?:ed)?)\b")
AUDIT_PATH = pathlib.Path(__file__).resolve().parents[1] / "audit.log"


@dataclass
class Session:
    user_id: str
    state: str = IDLE
    tx: dict = field(default_factory=dict)   # private working data; never given to the NLU
    fails: int = 0
    last_result: dict | None = None          # filled after a payment attempt (for receipts / UI)
    lang: str = "en"                         # "en" | "ne": the language the assistant speaks


@dataclass
class Reply:
    speech: str          # what the TTS says (the only thing the user hears)
    state: str
    expect: str          # "voice" | "otp_text" | "none"
    done: bool = False   # a transaction just finished (or was cancelled)
    end: bool = False    # the user chose to finish: switch the microphone off


def _audit(event: str, user_id: str, **kw):
    rec = {"ts": time.time(), "event": event, "user": user_id, **kw}
    with open(AUDIT_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


class DialogEngine:
    def __init__(self, nlu, bank, billers, otp):
        self.nlu, self.bank, self.billers, self.otp = nlu, bank, billers, otp

    # ---------- helpers ----------
    @staticmethod
    def _m(s: Session, key: str, **kw) -> str:
        return M.render(s.lang, key, **kw)

    def _r(self, s: Session, text: str, expect: str = "voice", done: bool = False, end: bool = False) -> Reply:
        return Reply(text, s.state, expect, done, end)

    def greeting(self, lang: str = "en") -> Reply:
        return Reply(M.render(lang, "greeting"), IDLE, "voice")

    # ---------- entry points ----------
    def handle_voice(self, s: Session, transcript: str) -> Reply:
        intent = self.nlu.parse(transcript, EXPECT[s.state])   # transcript only!
        if BYE_RE.search(transcript.lower()):
            return self._end(s)
        if s.state == CONTINUE:
            return self._on_continue(s, intent, transcript)
        if intent.name == "cancel":
            return self._end(s) if s.state == IDLE else self._cancel(s)
        if s.state == AWAIT_OTP:
            return self._r(s, self._m(s, "otp_type_only"), "otp_text")
        if s.state == CONFIRM:
            return self._on_confirm(s, intent)
        if s.state == CHOICE:
            return self._on_choice(s, intent)
        if s.state == CONFIRM_CURRENCY:
            return self._on_currency(s, intent)
        if s.state == DISAMBIGUATE:
            return self._on_disambiguate(s, intent)
        if s.state == CONFIRM_NAME:
            return self._on_confirm_name(s, intent, transcript)

        if s.state == IDLE:
            if intent.name == "transfer":
                s.tx = {"kind": "transfer"}
            elif intent.name == "pay_bill":
                s.tx = {"kind": "bill"}
            else:
                return self._r(s, self._m(s, "idle_help"))
            self._merge(s, intent.slots)
        else:
            self._merge(s, intent.slots)
            if intent.name == "unknown":
                return self._ask(s, prefix=True)
        return self._advance(s)

    def handle_otp(self, s: Session, otp: str) -> Reply:
        if s.state != AWAIT_OTP:
            return self._r(s, self._m(s, "no_code"))
        res = self.otp.verify(s.user_id, otp)
        if res == "ok":
            _audit("otp_ok", s.user_id)
            return self._execute(s)
        if res == "invalid":
            return self._r(s, self._m(s, "otp_wrong"), "otp_text")
        _audit("otp_fail", s.user_id, reason=res)
        return self._cancel(s, "otp_failed")

    # ---------- slot handling ----------
    def _merge(self, s: Session, slots: dict):
        slots = dict(slots)
        stated = slots.pop("currency_stated", False)
        slots.pop("ordinal", None)
        if "account_no" in slots or "recipient_name" in slots:     # a new recipient replaces the old one
            for k in ("contact", "_announced", "suggest"):
                s.tx.pop(k, None)
        if "account_no" in slots:
            slots.pop("recipient_name", None)                      # an account number beats a name
        if "amount" in slots:
            # Answering "how many rupees?" already fixes the currency; otherwise it must be said.
            s.tx["currency_ok"] = bool(stated) or s.state == ASK_AMOUNT
        s.tx.update(slots)

    # ---------- flow ----------
    def _advance(self, s: Session) -> Reply:
        r = self._advance_core(s)
        tx, L = s.tx, s.lang
        contact = tx.get("contact")
        if r.state == CONFIRM:
            tx["_announced"] = True                      # the confirmation names them in full
        elif contact and not tx.get("_announced") and tx.get("recipient") is not None:
            tx["_announced"] = True                      # "Found Sita Koirala." then the next question
            found = self._m(s, "found", name=M.person(L, contact.name, contact.name_ne))
            r = Reply(f"{found} {r.speech}", r.state, r.expect, r.done, r.end)
        return r

    def _advance_core(self, s: Session) -> Reply:
        tx, L = s.tx, s.lang
        if tx["kind"] == "transfer":
            if "account_no" not in tx:
                if tx.get("recipient_name"):
                    r = self._resolve_contact(s)
                    if r:
                        return r
                else:
                    s.state = ASK_ACCOUNT
                    return self._r(s, self._m(s, "ask_recipient"))
            if "recipient" not in tx:
                info = self.bank.validate_account(tx["account_no"])
                me = self.bank.source_account(s.user_id)
                if info is None or (me and info.account_no == me.account_no):
                    return self._validation_failed(s, ASK_ACCOUNT, "vf_account")
                tx["recipient"] = info
            if "amount" not in tx:
                s.state = ASK_AMOUNT
                return self._r(s, self._m(s, "how_much_send"))
        else:
            if "biller" not in tx:
                s.state = ASK_BILLER
                names = ", ".join(M.biller(L, b) for b in self.billers.list_billers())
                return self._r(s, self._m(s, "which_bill", names=names))
            if "customer_id" not in tx:
                s.state = ASK_CUSTOMER
                return self._r(s, self._m(s, "say_customer", biller=M.biller(L, tx["biller"])))
            if "bill" not in tx:
                bill = self.billers.lookup_bill(tx["biller"], tx["customer_id"])
                if bill is None:
                    return self._validation_failed(s, ASK_CUSTOMER, "vf_customer")
                tx["bill"] = bill
                if bill.amount_due > 0:
                    tx["amount"] = bill.amount_due
                    tx["currency_ok"] = True        # amount came from the biller, not from speech
            if "amount" not in tx:
                s.state = ASK_AMOUNT
                return self._r(s, self._m(s, "how_much_pay"))

        if not tx.get("currency_ok"):
            s.state = CONFIRM_CURRENCY
            return self._r(s, self._m(s, "you_said", num=M.num(L, tx["amount"])))
        if tx["amount"] > config.MAX_SINGLE_TRANSFER_NPR:
            tx.pop("amount")
            s.state = ASK_AMOUNT
            return self._r(s, self._m(s, "over_limit"))
        return self._confirm(s)

    # ----- recipient by name -----
    def _describe(self, s: Session, cands: list) -> str:
        L = s.lang
        dup = len({c.name.lower() for c in cands}) < len(cands)
        out = []
        for i, c in enumerate(cands, 1):
            extra = (self._m(s, "dup_extra", bank=M.bank(L, c.bank), last4=M.digits(L, c.account_no[-4:]))
                     if dup else "")
            out.append(f"{M.num(L, i)}, {M.person(L, c.name, c.name_ne)}{extra}")
        return M.sep(L).join(out)

    def _resolve_contact(self, s: Session) -> Reply | None:
        spoken, L = s.tx["recipient_name"], s.lang
        contacts = self.bank.contacts(s.user_id)
        cands = [c for c in contacts if phonetic_match(spoken, c.name)]
        if len(cands) == 1:                                     # exactly one: take it and carry on
            s.tx.update(account_no=cands[0].account_no, contact=cands[0], _announced=False)
            s.tx.pop("recipient_name", None)
            return None                                         # the account is still validated next
        if not cands:
            best = best_suggestion(spoken, contacts)
            if best:
                s.tx["suggest"] = best
                s.state = CONFIRM_NAME
                return self._r(s, self._m(s, "did_you_mean", spoken=M.spoken_name(L, spoken),
                                          name=M.person(L, best.name, best.name_ne)))
            return self._validation_failed(s, ASK_ACCOUNT, "vf_contact", spoken=M.spoken_name(L, spoken))
        s.tx["candidates"], s.tx["dis_tries"] = cands, s.tx.get("dis_tries", 0)
        s.state = DISAMBIGUATE
        return self._r(s, self._m(s, "found_n", n=M.num(L, len(cands)), spoken=M.spoken_name(L, spoken),
                                  list=self._describe(s, cands)))

    def _on_disambiguate(self, s: Session, intent) -> Reply:
        cands = s.tx["candidates"]
        pick = None
        o = intent.slots.get("ordinal")
        if o == -1:
            pick = cands[-1]
        elif o and 1 <= o <= len(cands):
            pick = cands[o - 1]
        elif intent.slots.get("recipient_name"):
            narrowed = [c for c in cands if phonetic_match(intent.slots["recipient_name"], c.name)]
            if len(narrowed) == 1:
                pick = narrowed[0]
            elif narrowed:
                cands = s.tx["candidates"] = narrowed
        if pick:
            s.tx.update(account_no=pick.account_no, contact=pick, _announced=False)
            for k in ("candidates", "recipient_name", "dis_tries"):
                s.tx.pop(k, None)
            return self._advance(s)
        s.tx["dis_tries"] = s.tx.get("dis_tries", 0) + 1
        if s.tx["dis_tries"] >= 3:
            return self._validation_failed(s, ASK_ACCOUNT, "vf_trouble")
        return self._r(s, self._m(s, "which_again", list=self._describe(s, cands)))

    def _on_confirm_name(self, s: Session, intent, transcript: str) -> Reply:
        """'I could not find X. Did you mean Y?'"""
        if intent.name == "yes":
            c = s.tx.pop("suggest")
            s.tx.pop("recipient_name", None)
            s.tx.update(account_no=c.account_no, contact=c, _announced=False)
            return self._advance(s)
        if intent.name == "no":
            s.tx.pop("suggest", None)
            s.tx.pop("recipient_name", None)
            s.state = ASK_ACCOUNT
            return self._r(s, f"{self._m(s, 'ok')} {self._m(s, 'ask_recipient')}")
        alt = self.nlu.parse(transcript, "recipient")           # they said another name or number instead
        if alt.slots.get("recipient_name") or alt.slots.get("account_no"):
            s.tx.pop("suggest", None)
            self._merge(s, alt.slots)
            return self._advance(s)
        return self._r(s, self._m(s, "say_yes_no"))

    # ----- failures / confirmations -----
    def _validation_failed(self, s: Session, retry_to: str, key: str, **kw) -> Reply:
        s.fails += 1
        for k in ("account_no", "recipient", "recipient_name", "candidates", "dis_tries",
                  "customer_id", "bill", "contact", "_announced", "suggest"):
            s.tx.pop(k, None)
        s.tx["retry_to"] = retry_to
        _audit("validation_failed", s.user_id, kind=s.tx["kind"], fails=s.fails)
        msg = self._m(s, key, **kw)
        if s.fails < config.MAX_ACCOUNT_RETRIES:
            s.state = retry_to
            tail = "another_contact" if retry_to == ASK_ACCOUNT else "another_customer"
            return self._r(s, f"{msg} {self._m(s, tail)}")
        s.state = CHOICE
        return self._r(s, f"{msg} {self._m(s, 'try_or_cancel')}")

    def _on_currency(self, s: Session, intent) -> Reply:
        L = s.lang
        if intent.name == "yes":
            s.tx["currency_ok"] = True
            return self._advance(s)
        if intent.name == "no":
            s.tx.pop("amount", None)
            s.tx.pop("currency_ok", None)
            s.state = ASK_AMOUNT
            return self._r(s, f"{self._m(s, 'ok')} {self._m(s, 'how_many')}")
        return self._r(s, self._m(s, "yes_if_rupees", num=M.num(L, s.tx["amount"])))

    def _confirm(self, s: Session) -> Reply:
        tx, L = s.tx, s.lang
        s.state = CONFIRM
        amt = M.amount(L, tx["amount"])
        if tx["kind"] == "transfer":
            r, c = tx["recipient"], tx.get("contact")
            name = M.person(L, c.name, c.name_ne) if c else M.masked(L, r.holder_name, r.name_ne)
            text = self._m(s, "confirm_transfer", amt=amt, name=name, bank=M.bank(L, r.bank),
                           last4=M.digits(L, r.account_no[-4:]))
        else:
            b = tx["bill"]
            text = self._m(s, "confirm_bill", amt=amt, biller=M.biller(L, tx["biller"]),
                           name=M.masked(L, b.customer_name, b.name_ne),
                           last4=M.digits(L, b.customer_id[-4:]))
        return self._r(s, text)

    def _on_confirm(self, s: Session, intent) -> Reply:
        if intent.name == "yes":
            s.tx["idem"] = uuid.uuid4().hex     # one key per confirmed payment => no double-spend
            if self.otp.required(s.tx["amount"]):
                self.otp.issue(s.user_id)
                s.state = AWAIT_OTP
                return self._r(s, self._m(s, "otp_sent"), "otp_text")
            return self._execute(s)
        if intent.name == "no":
            s.fails = 0
            retry_to = ASK_ACCOUNT if s.tx["kind"] == "transfer" else ASK_CUSTOMER
            for k in ("account_no", "recipient", "recipient_name", "customer_id", "bill", "amount",
                      "currency_ok", "contact", "_announced"):
                s.tx.pop(k, None)
            s.state = retry_to
            again = "ask_recipient" if retry_to == ASK_ACCOUNT else "ask_customer_again"
            return self._r(s, f"{self._m(s, 'ok')} {self._m(s, again)}")
        return self._r(s, self._m(s, "confirm_again"))

    def _on_choice(self, s: Session, intent) -> Reply:
        if intent.name in ("retry", "yes"):
            s.fails = 0
            s.state = s.tx.get("retry_to", ASK_ACCOUNT)
            if s.state == ASK_ACCOUNT:
                return self._r(s, self._m(s, "ask_recipient"))
            return self._r(s, f"{self._m(s, 'ok')} {self._m(s, 'ask_customer')}")
        return self._r(s, self._m(s, "retry_prompt"))

    def _execute(self, s: Session) -> Reply:
        tx, L = s.tx, s.lang
        if tx["kind"] == "transfer":
            res = self.bank.transfer(s.user_id, tx["recipient"].account_no, tx["amount"], tx["idem"])
        else:
            res = self.billers.pay_bill(s.user_id, tx["biller"], tx["bill"].customer_id, tx["amount"], tx["idem"])
        _audit("executed", s.user_id, kind=tx["kind"], amount=tx["amount"], ok=res.ok, ref=res.reference,
               reason=res.reason)
        if tx["kind"] == "transfer":
            c = tx.get("contact")
            to = c.name if c else M.masked("en", tx["recipient"].holder_name)
        else:
            to = f"{tx['biller']} bill"
        s.last_result = {"ok": res.ok, "kind": tx["kind"], "amount": tx["amount"], "ref": res.reference,
                         "reason": res.reason, "to": to}
        s.tx, s.fails, s.state = {}, 0, CONTINUE
        if res.ok:
            text = self._m(s, "done_ok", ref=M.digits("en", res.reference[-4:]))
        else:
            text = self._m(s, "fail_balance" if res.reason == "insufficient_funds" else "fail_generic")
        return self._r(s, f"{text} {self._m(s, 'continue_q')}", done=True)

    def _ask(self, s: Session, prefix: bool = False) -> Reply:
        prompts = {ASK_ACCOUNT: "ask_recipient", ASK_AMOUNT: "ask_amount", ASK_BILLER: "ask_biller",
                   ASK_CUSTOMER: "ask_customer"}
        text = self._m(s, prompts.get(s.state, "idle_help"))
        return self._r(s, f"{self._m(s, 'not_caught')} {text}" if prefix else text)

    # ----- finishing -----
    def _cancel(self, s: Session, key: str = "cancelled") -> Reply:
        self.otp.clear(s.user_id)
        _audit("cancelled", s.user_id)
        s.tx, s.fails, s.state = {}, 0, CONTINUE
        return self._r(s, f"{self._m(s, key)} {self._m(s, 'continue_q')}", done=True)

    def _on_continue(self, s: Session, intent, transcript: str) -> Reply:
        """'Would you like to make another transaction, or end?'"""
        low = transcript.lower()
        if intent.name in ("yes", "retry"):
            s.state = IDLE
            return self._r(s, self._m(s, "continue_yes"))
        if intent.name in ("transfer", "pay_bill"):         # they just asked for the next payment
            s.state = IDLE
            return self.handle_voice(s, transcript)
        if intent.name in ("no", "cancel") or FINISH_RE.search(low):
            return self._end(s)
        return self._r(s, self._m(s, "continue_unclear"))

    def _end(self, s: Session) -> Reply:
        self.otp.clear(s.user_id)
        _audit("session_end", s.user_id)
        s.tx, s.fails, s.state = {}, 0, IDLE
        return self._r(s, self._m(s, "goodbye"), "none", done=True, end=True)
