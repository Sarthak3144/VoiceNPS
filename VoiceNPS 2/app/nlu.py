"""Command understanding ("the AI").

It receives ONLY the transcript of what the user said plus a hint about which slot the dialog
is waiting for. It returns an Intent. It never sees balances, contacts, OTPs, or account data,
and it cannot move money: the deterministic dialog engine resolves names against the user's
contacts and decides what happens next, and the user confirms every sensitive step by voice.
"""
import json
import os
import re
from dataclasses import dataclass, field
from difflib import get_close_matches

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
        "eighty": 80, "ninety": 90}
SCALES = {"thousand": 1_000, "lakh": 100_000, "lac": 100_000, "million": 1_000_000}
DIGIT_WORDS = {**{k: str(v) for k, v in UNITS.items() if v <= 9}, "oh": "0", "o": "0"}

YES = {"yes", "yeah", "yep", "confirm", "correct", "ok", "okay", "sure", "proceed", "right", "haan", "ho"}
NO = {"no", "nope", "wrong", "incorrect", "nahi", "hoina"}
CANCEL = {"cancel", "stop", "terminate", "abort", "quit", "exit", "end"}
RETRY = {"retry", "again", "another", "different", "continue", "more"}

CURRENCY_RE = re.compile(r"\b(?:rs|nrs|npr|rupees?|rupaiya|rupaiyan)\b|₹|रु|रू")
TRANSFER_VERBS = ["send", "transfer", "remit", "give", "pay"]
ORDINALS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4,
            "last": -1}
# Words that are never part of a person's name.
NAME_STOP = {"to", "into", "account", "acc", "number", "no", "the", "my", "a", "an", "please", "money",
             "rupees", "rupee", "rs", "nrs", "npr", "and", "send", "transfer", "pay", "remit", "give",
             "it", "that", "one", "sir", "madam", "dai", "didi", "bhai", "ji", "sathi", "for", "of", "number",
             "option", "yes", "no", "hajur", "wala", "i", "want", "would", "like", "can", "you", "hey",
             "hello", "now", "today", "some", "amount", "from", "me", "bank", "also", "need", "make", "do"}

BILLERS = {
    "electricity": ["electricity", "electric", "nea", "light bill", "power"],
    "internet": ["internet", "wifi", "wi-fi", "broadband", "worldlink", "subisu", "vianet"],
    "water": ["water", "khanepani"],
    "mobile topup": ["topup", "top up", "recharge", "mobile", "ntc", "ncell"],
}


@dataclass
class Intent:
    name: str                       # transfer | pay_bill | yes | no | cancel | retry | slots | unknown
    slots: dict = field(default_factory=dict)
    # slots: account_no, recipient_name, amount, currency_stated, biller, customer_id, ordinal


def extract_amount_words(tokens: list[str]) -> float | None:
    """Find the first run of number words ('two thousand five hundred') anywhere in the sentence."""
    total, cur, seen, started = 0, 0, False, False
    for t in tokens + ["#"]:
        if t in UNITS or t in TENS or t in SCALES or t == "hundred" or (started and t == "and"):
            started = True
            if t in UNITS: cur += UNITS[t]; seen = True
            elif t in TENS: cur += TENS[t]; seen = True
            elif t == "hundred": cur = max(cur, 1) * 100; seen = True
            elif t in SCALES: total += max(cur, 1) * SCALES[t]; cur = 0; seen = True
        elif started:
            break
    return float(total + cur) if seen else None


def spoken_digits(text: str) -> str:
    """'one two three' -> '123'; also keeps literal digits. Handles 'double'/'triple'."""
    out, mult = [], 1
    for tok in re.findall(r"[a-z]+|\d+", text.lower()):
        if tok == "double": mult = 2
        elif tok == "triple": mult = 3
        elif tok.isdigit(): out.append(tok * mult); mult = 1
        elif tok in DIGIT_WORDS: out.append(DIGIT_WORDS[tok] * mult); mult = 1
    return "".join(out)


def parse_amount(text: str) -> float | None:
    t = text.lower().replace(",", "")
    t = re.sub(r"\d{9,}", " ", t)                      # never mistake an account number for an amount
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lac)?\b", t)
    if m:
        mult = {"k": 1000, "thousand": 1000, "lakh": 100000, "lac": 100000}.get(m.group(2), 1)
        return float(m.group(1)) * mult
    return extract_amount_words(re.findall(r"[a-z]+", t))


def clean_name(text: str) -> str:
    toks = [w for w in re.findall(r"[a-z]+", text.lower())
            if w not in NAME_STOP and w not in UNITS and w not in TENS and w not in SCALES and w != "hundred"]
    return " ".join(toks)


def first_verb(tokens: list[str]) -> str | None:
    """Typo-tolerant: 'sedn' -> 'send'."""
    for tok in tokens[:6]:
        if tok in TRANSFER_VERBS:
            return tok
        m = get_close_matches(tok, TRANSFER_VERBS, n=1, cutoff=0.7)
        if m:
            return m[0]
    return None


class RuleNLU:
    """Fast, offline, deterministic, free. Good enough for a closed command set."""

    def parse(self, transcript: str, expecting: str | None = None) -> Intent:
        t = transcript.lower().strip()
        t = re.sub(r"(?<=\d)[,\-](?=\d)", "", t)          # "2,000" / "123-456" -> digits only
        words = re.findall(r"[a-z0-9']+", t)
        toks = set(words)

        if toks & CANCEL:
            return Intent("cancel")
        if expecting in ("yes_no", "retry_cancel"):
            if toks & RETRY: return Intent("retry")
            if toks & NO: return Intent("no")
            if toks & YES: return Intent("yes")

        if expecting == "choice":                       # "which Ramesh?" -> "second" / "Sharma"
            slots: dict = {}
            for w in words:
                if w in ORDINALS:
                    slots["ordinal"] = ORDINALS[w]; break
            if "ordinal" not in slots:
                m = re.search(r"\b(?:number|option)?\s*([1-9])\b", t)
                if m: slots["ordinal"] = int(m.group(1))
                elif len(words) <= 3 and (toks & set(UNITS)):
                    slots["ordinal"] = next(UNITS[w] for w in words if w in UNITS)
            name = clean_name(t)
            if name: slots["recipient_name"] = name
            return Intent("slots", slots) if slots else Intent("unknown")

        slots = {}
        biller = next((b for b, kws in BILLERS.items()
                       if any(re.search(r"\b" + re.escape(k) + r"\b", t) for k in kws)), None)
        if biller:
            slots["biller"] = biller

        verb = first_verb(words)
        # send / transfer / pay / remit / give all mean "move money to a person" ...
        # ... unless a biller or a bill word is present (electricity, internet, "bill", "recharge").
        bill_word = bool(re.search(r"\b(bills?|recharge|top ?up|topup)\b", t))
        is_bill = bool(biller) or bill_word
        is_transfer = (not is_bill) and verb is not None

        if expecting == "customer_id":
            d = spoken_digits(t)
            if d: slots["customer_id"] = d
        elif expecting in (None, "account", "recipient", "any"):
            lit = re.search(r"\d{9,}", t)
            accs = list(re.finditer(r"\b(?:to|into|account|acc)\b", t))
            m_acc = accs[-1] if accs else None
            if lit:
                digits = lit.group(0)
            elif m_acc:
                digits = spoken_digits(t[m_acc.start():])
            else:
                digits = spoken_digits(t) if expecting in ("account", "recipient") else ""
            if len(digits) >= 9:
                slots["account_no"] = digits
            elif is_transfer or expecting in ("account", "recipient"):
                m_to = re.search(r"\b(?:to|into)\b(.*)", t)
                name = clean_name(m_to.group(1) if m_to else t)
                if name:
                    slots["recipient_name"] = name

        if expecting == "amount" or is_transfer or is_bill:
            a = parse_amount(t)
            if a and a > 0:
                slots["amount"] = a
                slots["currency_stated"] = bool(CURRENCY_RE.search(t))

        if is_transfer: return Intent("transfer", slots)
        if is_bill: return Intent("pay_bill", slots)
        if slots: return Intent("slots", slots)
        if toks & YES: return Intent("yes")
        if toks & NO: return Intent("no")
        return Intent("unknown")


class LLMNLU(RuleNLU):
    """Optional: let an LLM classify the transcript, falling back to rules.
    The prompt contains ONLY the transcript, so private data cannot leak by construction."""

    PROMPT = ("Classify this payment voice command. Reply with JSON only: "
              '{"name": "transfer|pay_bill|yes|no|cancel|retry|slots|unknown", '
              '"slots": {"account_no": str?, "recipient_name": str?, "amount": number?, '
              '"currency_stated": bool?, "biller": str?, "customer_id": str?}}. '
              "currency_stated is true only if the user said rupees/Rs. "
              "Never invent values the user did not say. Transcript: ")

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = os.getenv("NLU_MODEL", "claude-haiku-5-5")

    def parse(self, transcript, expecting=None):
        if expecting in ("yes_no", "retry_cancel", "choice", "customer_id", "amount"):
            return super().parse(transcript, expecting)     # simple slots: rules are exact and free
        try:
            r = self.client.messages.create(model=self.model, max_tokens=200,
                                            messages=[{"role": "user", "content": self.PROMPT + transcript}])
            d = json.loads(r.content[0].text)
            return Intent(d["name"], d.get("slots", {}))
        except Exception:
            return super().parse(transcript, expecting)
