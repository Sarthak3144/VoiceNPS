"""Nepali language support. No external dependencies.

 * translit()              Devanagari word  -> Latin letters   (सीता -> sita)
 * latin_to_devanagari()   Latin name       -> Devanagari      (Sita Koirala -> सीता कोइराला)
 * number_words_ne()       2500 -> दुई हजार पाँच सय
 * normalize_transcript()  Nepali speech (Devanagari or romanised) -> the English command words the
                           rule engine understands. Plain English passes through unchanged.
"""
import re

DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
DEV_RE = re.compile(r"[ऀ-ॿ]")

# ------------------------------------------------------------------ Devanagari -> Latin
_V = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri"}
_M = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ृ": "ri"}
_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
      "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
      "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
      "ष": "sh", "स": "s", "ह": "h"}
_SIGNS = {"ं": "n", "ँ": "n", "ः": "h"}
_VIRAMA, _NUKTA = "्", "़"


def translit(word: str) -> str:
    """Devanagari word -> Latin letters: सीता -> sita, भट्टराई -> bhattarai, कोइराला -> koirala."""
    word = word.translate(DEV_DIGITS)
    out, i, n = [], 0, len(word)
    while i < n:
        ch = word[i]
        if ch in _C:
            out.append(_C[ch]); j = i + 1
            if j < n and word[j] == _NUKTA:
                j += 1
            if j < n and word[j] in _M:
                out.append(_M[word[j]]); j += 1
            elif j < n and word[j] == _VIRAMA:
                j += 1
            elif j < n:                       # inherent 'a' (dropped at the end of a word)
                out.append("a")
            i = j
        elif ch in _V:
            out.append(_V[ch]); i += 1
        elif ch in _SIGNS:
            out.append(_SIGNS[ch]); i += 1
        elif ch.isdigit() or ch.isascii():
            out.append(ch); i += 1
        else:
            i += 1
    return "".join(out)


def roman(w: str) -> str:
    """Lower-case Latin form of a word that may be Devanagari."""
    return translit(w).lower() if DEV_RE.search(w) else w.lower()


# ------------------------------------------------------------------ Latin -> Devanagari (names)
# Known names first (exact, reviewed spellings); a rule-based fallback handles everything else.
NAME_WORDS_NE = {
    "ram": "राम", "rama": "रमा", "ramesh": "रमेश", "suresh": "सुरेश", "mahesh": "महेश", "dinesh": "दिनेश",
    "rajesh": "राजेश", "ganesh": "गणेश", "hari": "हरि", "krishna": "कृष्ण", "gopal": "गोपाल", "shyam": "श्याम",
    "sita": "सीता", "gita": "गीता", "rita": "रीता", "anita": "अनिता", "sunita": "सुनिता", "sarita": "सरिता",
    "kabita": "कविता", "laxmi": "लक्ष्मी", "saraswati": "सरस्वती", "binod": "विनोद", "bikash": "विकास",
    "prakash": "प्रकाश", "anil": "अनिल", "sunil": "सुनिल", "sanjay": "सञ्जय", "sandip": "सन्दीप",
    "sagar": "सागर", "sarthak": "सार्थक", "bishal": "विशाल", "rohan": "रोहन", "aarav": "आरव", "sabin": "सबिन",
    "sharma": "शर्मा", "koirala": "कोइराला", "thapa": "थापा", "bhattarai": "भट्टराई", "adhikari": "अधिकारी",
    "poudel": "पौडेल", "gurung": "गुरुङ", "tamang": "तामाङ", "rai": "राई", "limbu": "लिम्बु",
    "shrestha": "श्रेष्ठ", "karki": "कार्की", "basnet": "बस्नेत", "khadka": "खड्का", "pandey": "पाण्डे",
    "joshi": "जोशी", "acharya": "आचार्य", "regmi": "रेग्मी", "subedi": "सुवेदी", "neupane": "न्यौपाने",
    "himalayan": "हिमालयन", "traders": "ट्रेडर्स", "pvt": "प्राइभेट", "ltd": "लिमिटेड", "self": "आफैँ",
    "bank": "बैंक", "demo": "डेमो", "sample": "स्याम्पल",
    "electricity": "बिजुली", "internet": "इन्टरनेट", "water": "खानेपानी",
}
_LC = [("chh", "छ"), ("ksh", "क्ष"), ("shr", "श्र"), ("sh", "श"), ("ch", "च"), ("kh", "ख"), ("gh", "घ"),
       ("jh", "झ"), ("th", "थ"), ("dh", "ध"), ("ph", "फ"), ("bh", "भ"), ("ng", "ङ"), ("tr", "त्र"), ("gy", "ज्ञ")]
_SC = dict(k="क", g="ग", c="क", j="ज", t="त", d="द", n="न", p="प", b="ब", m="म", y="य", r="र", l="ल", v="व",
           w="व", s="स", h="ह", f="फ", z="ज", q="क", x="क्स")
_LV = [("aa", "ा", "आ"), ("ai", "ै", "ऐ"), ("au", "ौ", "औ"), ("ee", "ी", "ई"), ("ii", "ी", "ई"),
       ("oo", "ू", "ऊ"), ("ou", "ौ", "औ")]
_SV = {"a": ("", "अ"), "i": ("ि", "इ"), "u": ("ु", "उ"), "e": ("े", "ए"), "o": ("ो", "ओ")}


def _rule_word(w: str) -> str:
    out, i, pending = [], 0, False        # pending: last glyph is a consonant carrying an inherent 'a'
    while i < len(w):
        for lat, dev in _LC:
            if w.startswith(lat, i):
                if pending:
                    out.append("्")
                out.append(dev); pending = True; i += len(lat); break
        else:
            ch = w[i]
            if ch in _SC:
                if pending:
                    out.append("्")
                out.append(_SC[ch]); pending = True; i += 1
                continue
            for lat, matra, indep in _LV:
                if w.startswith(lat, i):
                    out.append(matra if pending else indep); pending = False; i += len(lat); break
            else:
                if ch in _SV:
                    matra, indep = _SV[ch]
                    final = i == len(w) - 1
                    if pending:
                        out.append("ा" if (ch == "a" and final) else matra)
                    else:
                        out.append(indep)
                    pending = False
                i += 1
    return "".join(out)


def latin_to_devanagari(text: str) -> str:
    """'Sita Koirala' -> 'सीता कोइराला'. Unknown words use a rule-based guess (supply real
    Devanagari names through the bank adapter for best results)."""
    words = []
    for w in re.findall(r"[A-Za-z]+|\d+|[ऀ-ॿ]+", text):
        if DEV_RE.search(w):
            words.append(w)
        elif w.isdigit():
            words.append(number_words_ne(int(w)))
        else:
            words.append(NAME_WORDS_NE.get(w.lower()) or _rule_word(w.lower()))
    return " ".join(words)


# ------------------------------------------------------------------ numbers in Nepali words
NE_0_99 = (
    "शून्य एक दुई तीन चार पाँच छ सात आठ नौ दश "
    "एघार बाह्र तेह्र चौध पन्ध्र सोह्र सत्र अठार उन्नाइस बीस "
    "एक्काइस बाइस तेइस चौबीस पच्चीस छब्बीस सत्ताइस अठ्ठाइस उनन्तीस तीस "
    "एकतीस बत्तीस तेत्तीस चौँतीस पैँतीस छत्तीस सतत्तीस अठतीस उनन्चालीस चालीस "
    "एकचालीस बयालीस त्रिचालीस चौवालीस पैँतालीस छयालीस सतचालीस अठचालीस उनन्चास पचास "
    "एकाउन्न बाउन्न त्रिपन्न चौवन्न पचपन्न छपन्न सन्ताउन्न अन्ठाउन्न उनान्साठी साठी "
    "एकसट्ठी बैसट्ठी त्रिसट्ठी चौँसट्ठी पैँसट्ठी छयसट्ठी सतसट्ठी अठसट्ठी उनान्सत्तरी सत्तरी "
    "एकहत्तर बहत्तर त्रिहत्तर चौहत्तर पचहत्तर छयहत्तर सतहत्तर अठहत्तर उनासी असी "
    "एकासी बयासी त्रियासी चौरासी पचासी छयासी सतासी अठासी उनान्नब्बे नब्बे "
    "एकानब्बे बयानब्बे त्रियानब्बे चौरानब्बे पञ्चानब्बे छयानब्बे सन्तानब्बे अन्ठानब्बे उनान्सय"
).split()
assert len(NE_0_99) == 100
DIGIT_WORDS_NE = NE_0_99[:10]


def number_words_ne(n: int) -> str:
    """2500 -> 'दुई हजार पाँच सय'; 100000 -> 'एक लाख'."""
    n = int(n)
    if n < 0:
        return "ऋण " + number_words_ne(-n)
    if n < 100:
        return NE_0_99[n]
    parts = []
    for unit, name in ((10 ** 7, "करोड"), (10 ** 5, "लाख"), (1000, "हजार"), (100, "सय")):
        q, n = divmod(n, unit)
        if q:
            parts.append(f"{number_words_ne(q)} {name}")
    if n:
        parts.append(NE_0_99[n])
    return " ".join(parts)


def digits_words_ne(s: str) -> str:
    """'0987' -> 'शून्य नौ आठ सात'; non-digits are skipped (references are shown on screen instead)."""
    return " ".join(DIGIT_WORDS_NE[int(c)] for c in s if c.isdigit())


# ------------------------------------------------------------------ Nepali speech -> English command words
def _w(s):
    return set(s.split())


_YES = _w("हो हुन्छ ठिक ठीक हजुर हस् अवश्य पक्का ho huncha hunchha thik thikai hajur")
_NO = _w("होइन छैन हुँदैन हुदैन पर्दैन hoina chaina hudaina hundaina pardaina")
_CANCEL = _w("रद्द रद्ध बन्द छोड radda banda chod")
_END = _w("अन्त्य समाप्त सकियो सक्यो बिदा विदा धन्यवाद antya samapta sakiyo bida dhanyabad")
_RETRY = _w("फेरि फेरी अर्को pheri feri arko")
_ORD = {"पहिलो": "first", "पहिला": "first", "दोस्रो": "second", "दोश्रो": "second", "दोस्रा": "second",
        "तेस्रो": "third", "चौथो": "fourth", "अन्तिम": "last", "अन्तिमको": "last",
        "pahilo": "first", "dosro": "second", "tesro": "third", "chautho": "fourth", "antim": "last"}
_BILLERS = {"बिजुली": "electricity", "बिजुलीको": "electricity", "बत्ती": "electricity", "bijuli": "electricity",
            "इन्टरनेट": "internet", "इन्टरनेटको": "internet", "वाइफाइ": "wifi", "वाईफाई": "wifi", "वाइफाई": "wifi",
            "पानी": "water", "खानेपानी": "water", "pani": "water", "khanepani": "water",
            "रिचार्ज": "recharge", "टपअप": "topup", "मोबाइल": "mobile", "बिल": "bill", "बिलको": "bill"}
_HONOR = _w("दाइ दाजु दिदी बहिनी भाइ जी ज्यू सर म्याडम dai daju didi bhai bahini ji sir madam")
_FILLER = _w("मलाई कृपया म गर गर्नु गर्नुहोस् गर्दिनु गर्दिनुहोस् अब अनि र please चाहन्छु चाहन्छ चाहन्छौं चाहनुहुन्छ चाहियो छु गर्छु गर्ने गर्न")
_MONEY = _w("पैसा रकम paisa raqam")
_GIVE = _w("दिनुहोस् दिनुस् दिनु देऊ dinus dinu deu dinuhos")
_NUM = {"शून्य": 0, "एक": 1, "दुई": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पाच": 5, "सात": 7, "आठ": 8, "नौ": 9,
        "दश": 10, "दस": 10, "एघार": 11, "बाह्र": 12, "तेह्र": 13, "चौध": 14, "पन्ध्र": 15, "सोह्र": 16, "सत्र": 17,
        "अठार": 18, "उन्नाइस": 19, "बीस": 20, "तीस": 30, "चालीस": 40, "पचास": 50, "साठी": 60, "सत्तरी": 70,
        "असी": 80, "अस्सी": 80, "नब्बे": 90, "सय": 100, "हजार": 1000, "लाख": 100000,
        "ek": 1, "dui": 2, "tin": 3, "teen": 3, "char": 4, "panch": 5, "paanch": 5, "saat": 7, "aath": 8,
        "nau": 9, "das": 10, "bis": 20, "tis": 30, "chalis": 40, "pachas": 50, "saya": 100, "sai": 100,
        "hajar": 1000, "lakh": 100000}
# every word of the 0-99 table is also understood (so "पचपन्न हजार" works)
for _i, _word in enumerate(NE_0_99):
    _NUM.setdefault(_word, _i)
_NUM.pop("छ", None)            # "छ" is also the verb "is": only a number when digits are expected
_NUMV = {**_NUM, "छ": 6, "छः": 6, "छह": 6, "chha": 6}
_DIGIT_CTX = ("customer_id", "recipient", "account")
_ROMAN_MARKERS = _w("lai pathau pathaideu pathaidinus pathaunus rupaiya rupaiyan rupiya tirnu hajar saya "
                    "pheri feri hoina chaina huncha hunchha paisa")


def _num_value(words):
    total, cur = 0, 0
    for x in words:
        v = _NUMV[x]
        if x in ("सय", "saya", "sai"):
            cur = max(cur, 1) * 100
        elif v >= 1000:
            total += max(cur, 1) * v; cur = 0
        else:
            cur += v
    return total + cur


def _classify(raw: str, lw: str):
    if raw == "₹" or lw in ("rs", "rupees", "rupee") or raw in ("रु", "रू") or raw.startswith(("रुपै", "रुपि", "रुपय")) \
            or lw.startswith(("rupai", "rupiy", "rupay")):
        return "cur", "rupees"
    if raw.startswith(("पठा", "ट्रान्सफर", "ट्रांसफर", "भेज")) or lw.startswith(("pathau", "pathai", "patha")) \
            or raw in _GIVE or lw in _GIVE or lw in ("send", "transfer", "remit", "give"):
        return "send", "send"
    if raw.startswith(("तिर", "भुक्तान", "पेमेन्ट")) or lw.startswith(("tir", "bhuktan", "payment")) or lw == "pay":
        return "pay", "pay"
    if raw in _MONEY or lw in _MONEY or lw == "money":
        return "skip", ""
    if raw in _NUM or lw in _NUM:
        return "num", raw if raw in _NUM else lw
    if raw in _BILLERS:
        return "biller", _BILLERS[raw]
    if lw in ("electricity", "internet", "wifi", "water", "recharge", "topup", "mobile", "bill"):
        return "biller", lw
    if raw in _ORD or lw in _ORD:
        return "word", _ORD.get(raw) or _ORD[lw]
    for words, out in ((_YES, "yes"), (_NO, "no"), (_CANCEL, "cancel"), (_END, "end"), (_RETRY, "try again")):
        if raw in words or lw in words:
            return "word", out
    if raw in _HONOR or lw in _HONOR or raw in _FILLER or lw in _FILLER:
        return "skip", ""
    if lw in ("to", "into"):
        return "to", ""
    return None


def normalize_transcript(text: str, expecting: str | None = None) -> str:
    """Turns Nepali (Devanagari or romanised) speech into the English command the engine understands.
    Plain English is returned unchanged. `expecting` says which answer the dialog is waiting for, so
    spoken digit sequences ("एक दुई तीन ...") become an account / customer number instead of a sum."""
    t = text.translate(DEV_DIGITS)
    toks = re.findall(r"[ऀ-ॿ]+|[A-Za-z]+|\d[\d.,]*|₹", t)
    low = [x.lower() for x in toks]
    if not DEV_RE.search(t) and not any(x in _ROMAN_MARKERS or x.startswith(("pathau", "pathai")) for x in low):
        return t                                  # plain English (Devanagari digits, if any, now 0-9)
    digit_ctx = expecting in _DIGIT_CTX
    items = []                                    # (kind, value)
    for raw, lw in zip(toks, low):
        if re.fullmatch(r"\d[\d.,]*", raw):
            items.append(("digits", raw.replace(",", "")))
        elif digit_ctx and raw in ("छ", "छः", "छह"):
            items.append(("num", raw))
        elif lw in ("लाई", "lai"):
            items.append(("to", ""))
        elif raw.endswith("लाई") and len(raw) > 3:
            items += [("name", translit(raw[:-3])), ("to", "")]
        elif lw.endswith("lai") and len(lw) > 4 and not DEV_RE.search(raw):
            items += [("name", lw[:-3]), ("to", "")]
        else:
            c = _classify(raw, lw)
            if c:
                items.append(c)
            elif DEV_RE.search(raw):
                items.append(("name", translit(raw)))
            else:
                items.append(("name", lw))
    # runs of single-digit words read one by one are an account / customer number, not an amount
    min_run = 3 if expecting == "customer_id" else 5
    collapsed, run = [], []

    def flush_run():
        if len(run) >= min_run and all(_NUMV[v] < 10 for v in run):
            collapsed.append(("digits", "".join(str(_NUMV[v]) for v in run)))
        else:
            collapsed.extend(("num", v) for v in run)
        run.clear()

    for k, v in items:
        if k == "num":
            run.append(v)
        else:
            flush_run(); collapsed.append((k, v))
    flush_run()
    # remaining runs of number words are one amount ("दुई हजार पाँच सय" -> 2500)
    merged, run = [], []
    for k, v in collapsed + [("end", "")]:
        if k == "num":
            run.append(v); continue
        if run:
            merged.append(("digits", str(_num_value(run)))); run = []
        if k != "end":
            merged.append((k, v))
    items = merged

    kinds = {k for k, _ in items}
    account = next((v for k, v in items if k == "digits" and len(v) >= 9), None)
    amount = next((v for k, v in items if k == "digits" and len(v) < 9), None)
    cur = "cur" in kinds
    names = []                                     # the name words right before the last "to" (लाई)
    for idx in range(len(items) - 1, -1, -1):
        if items[idx][0] == "to":
            j = idx - 1
            while j >= 0 and items[j][0] == "name":
                names.insert(0, items[j][1]); j -= 1
            break
    if "biller" not in kinds and (kinds & {"send", "pay"} or ("to" in kinds and (names or account))):
        parts = ["send"]
        if amount:
            parts += [amount] + (["rupees"] if cur else [])
        if account:
            parts += ["to", "account", account]
        elif names:
            parts += ["to", " ".join(n for n in names if n)]
        return " ".join(parts)
    out = []
    for k, v in items:
        if k in ("skip", "to") or not v:
            continue
        out.append(v if k != "cur" else "rupees")
    return " ".join(out) or text
