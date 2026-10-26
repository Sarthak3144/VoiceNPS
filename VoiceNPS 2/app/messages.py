"""Every sentence the assistant can say, in English ("en") and Nepali ("ne"), in ONE place.

The dialog engine never builds sentences itself: it asks for a message key plus values, and this
module renders it in the session's language. To add a language, add one more column here.
Placeholders in {braces} are filled in by render(); the Nepali text may leave one out.
"""
from .nepali import NAME_WORDS_NE, digits_words_ne, latin_to_devanagari, number_words_ne

LANGS = ("en", "ne")

MESSAGES = {
    "greeting": {
        "en": "Welcome to VoiceNPS. I can send money or pay bills like electricity and internet. What would you like to do?",
        "ne": "भ्वाइस एनपीएसमा स्वागत छ। म पैसा पठाउन वा बिजुली र इन्टरनेट जस्ता बिल तिर्न सक्छु। तपाईं के गर्न चाहनुहुन्छ?"},
    "idle_help": {
        "en": "I can send money or pay bills like electricity and internet. What would you like to do?",
        "ne": "म पैसा पठाउन वा बिजुली र इन्टरनेट जस्ता बिल तिर्न सक्छु। तपाईं के गर्न चाहनुहुन्छ?"},
    "not_caught": {
        "en": "Sorry, I didn't catch that.",
        "ne": "माफ गर्नुहोस्, मैले बुझिनँ।"},
    "ok": {"en": "Okay.", "ne": "ठिक छ।"},

    # ---- questions
    "ask_recipient": {
        "en": "Who would you like to send money to? Say a name, or an account number.",
        "ne": "तपाईं कसलाई पैसा पठाउन चाहनुहुन्छ? नाम वा खाता नम्बर भन्नुहोस्।"},
    "ask_amount": {
        "en": "Please say the amount in rupees.",
        "ne": "कृपया रकम रुपैयाँमा भन्नुहोस्।"},
    "ask_biller": {
        "en": "Which bill do you want to pay?",
        "ne": "तपाईं कुन बिल तिर्न चाहनुहुन्छ?"},
    "ask_customer": {
        "en": "Please say the customer number.",
        "ne": "कृपया ग्राहक नम्बर भन्नुहोस्।"},
    "ask_customer_again": {
        "en": "Please say the customer number again.",
        "ne": "कृपया ग्राहक नम्बर फेरि भन्नुहोस्।"},
    "how_much_send": {
        "en": "How many rupees would you like to send?",
        "ne": "तपाईं कति रुपैयाँ पठाउन चाहनुहुन्छ?"},
    "how_much_pay": {
        "en": "How many rupees would you like to pay?",
        "ne": "तपाईं कति रुपैयाँ तिर्न चाहनुहुन्छ?"},
    "how_many": {"en": "How many rupees?", "ne": "कति रुपैयाँ?"},
    "which_bill": {
        "en": "Which bill? You can say {names}.",
        "ne": "कुन बिल? तपाईं {names} भन्न सक्नुहुन्छ।"},
    "say_customer": {
        "en": "Please say your {biller} customer number.",
        "ne": "कृपया तपाईंको {biller} ग्राहक नम्बर भन्नुहोस्।"},
    "you_said": {
        "en": "You said {num}. Is that in rupees?",
        "ne": "तपाईंले {num} भन्नुभयो। त्यो रुपैयाँमा हो?"},
    "yes_if_rupees": {
        "en": "Please say yes if {num} is in rupees, or no to change it.",
        "ne": "{num} रुपैयाँ हो भने हो भन्नुहोस्, परिवर्तन गर्न होइन भन्नुहोस्।"},
    "over_limit": {
        "en": "That is above the single payment limit. Please say a smaller amount in rupees.",
        "ne": "यो एक पटकको भुक्तानी सीमाभन्दा बढी छ। कृपया रुपैयाँमा सानो रकम भन्नुहोस्।"},

    # ---- validation problems
    "vf_account": {
        "en": "I could not verify that account.",
        "ne": "मैले त्यो खाता प्रमाणित गर्न सकिनँ।"},
    "vf_customer": {
        "en": "I could not find that customer number.",
        "ne": "मैले त्यो ग्राहक नम्बर फेला पार्न सकिनँ।"},
    "vf_contact": {
        "en": "I could not find a contact named {spoken}.",
        "ne": "मैले {spoken} नाम भएको सम्पर्क फेला पार्न सकिनँ।"},
    "vf_trouble": {
        "en": "I am having trouble telling them apart.",
        "ne": "मलाई उनीहरूलाई छुट्याउन गाह्रो भइरहेको छ।"},
    "another_contact": {
        "en": "Please say another name or account number.",
        "ne": "कृपया अर्को नाम वा खाता नम्बर भन्नुहोस्।"},
    "another_customer": {
        "en": "Please say another customer number.",
        "ne": "कृपया अर्को ग्राहक नम्बर भन्नुहोस्।"},
    "try_or_cancel": {
        "en": "Do you want to try again, or cancel?",
        "ne": "के तपाईं फेरि प्रयास गर्न चाहनुहुन्छ, कि रद्द गर्ने?"},
    "retry_prompt": {
        "en": "Say try again, or cancel.",
        "ne": "फेरि प्रयास भन्नुहोस्, वा रद्द भन्नुहोस्।"},

    # ---- choosing between contacts
    "found_n": {
        "en": "I found {n} contacts named {spoken}. {list}. Which one?",
        "ne": "{spoken} नाम भएका {n} सम्पर्क फेला परे। {list}। कुन एउटा?"},
    "which_again": {
        "en": "Sorry, which one? {list}. You can say first, second, or the last name.",
        "ne": "माफ गर्नुहोस्, कुन एउटा? {list}। तपाईं पहिलो, दोस्रो, वा थर भन्न सक्नुहुन्छ।"},
    "dup_extra": {
        "en": ", {bank}, account ending {last4}",
        "ne": ", {bank}, खाताको अन्तिम अङ्क {last4}"},
    "found": {"en": "Found {name}.", "ne": "{name} भेटियो।"},
    "did_you_mean": {
        "en": "I could not find {spoken}. Did you mean {name}?",
        "ne": "मैले {spoken} फेला पार्न सकिनँ। के तपाईंको मतलब {name} हो?"},
    "say_yes_no": {
        "en": "Please say yes or no.",
        "ne": "कृपया हो वा होइन भन्नुहोस्।"},

    # ---- confirmation and OTP
    "confirm_transfer": {
        "en": "Send {amt} to {name}, {bank}, account ending {last4}. Say yes to confirm, or no to change.",
        "ne": "{name}लाई {amt} पठाउने हो? {bank}, खाताको अन्तिम अङ्क {last4}। पक्का गर्न हो भन्नुहोस्, परिवर्तन गर्न होइन भन्नुहोस्।"},
    "confirm_bill": {
        "en": "Pay {amt} for {biller} to {name}, customer number ending {last4}. Say yes to confirm, or no to change.",
        "ne": "{biller} बिल बापत {name}लाई {amt} तिर्ने हो? ग्राहक नम्बरको अन्तिम अङ्क {last4}। पक्का गर्न हो भन्नुहोस्, परिवर्तन गर्न होइन भन्नुहोस्।"},
    "confirm_again": {
        "en": "Please say yes to confirm, or cancel to stop.",
        "ne": "पक्का गर्न हो भन्नुहोस्, वा रोक्न रद्द भन्नुहोस्।"},
    "otp_sent": {
        "en": "A verification code was sent to your phone. Please type it on the screen.",
        "ne": "तपाईंको फोनमा प्रमाणीकरण कोड पठाइएको छ। कृपया स्क्रिनमा टाइप गर्नुहोस्।"},
    "otp_type_only": {
        "en": "Please type the code on your screen. Do not say it out loud. Say cancel to stop.",
        "ne": "कृपया कोड स्क्रिनमा टाइप गर्नुहोस्। ठूलो स्वरमा नभन्नुहोस्। रोक्न रद्द भन्नुहोस्।"},
    "otp_wrong": {
        "en": "That code is incorrect. Please type it again.",
        "ne": "कोड मिलेन। कृपया फेरि टाइप गर्नुहोस्।"},
    "otp_failed": {
        "en": "The code could not be verified, so the payment was cancelled.",
        "ne": "कोड प्रमाणित हुन सकेन, त्यसैले भुक्तानी रद्द गरियो।"},
    "no_code": {
        "en": "No code is needed right now.",
        "ne": "अहिले कुनै कोड चाहिँदैन।"},

    # ---- results
    "done_ok": {
        "en": "Done. Payment successful. Reference ending {ref}.",
        "ne": "सम्पन्न भयो। भुक्तानी सफल भयो। सन्दर्भ नम्बर स्क्रिनमा देखाइएको छ।"},
    "fail_balance": {
        "en": "Sorry, your balance is too low. Nothing was charged.",
        "ne": "माफ गर्नुहोस्, तपाईंको मौज्दात अपुग छ। कुनै रकम काटिएन।"},
    "fail_generic": {
        "en": "Sorry, the payment could not be completed. Nothing was charged.",
        "ne": "माफ गर्नुहोस्, भुक्तानी पूरा हुन सकेन। कुनै रकम काटिएन।"},
    "cancelled": {"en": "Okay, cancelled.", "ne": "ठिक छ, रद्द गरियो।"},

    # ---- continue or end
    "continue_q": {
        "en": "Would you like to make another transaction, or end?",
        "ne": "के तपाईं अर्को कारोबार गर्न चाहनुहुन्छ, कि अन्त्य गर्ने?"},
    "continue_yes": {
        "en": "Sure. What would you like to do?",
        "ne": "हुन्छ। तपाईं के गर्न चाहनुहुन्छ?"},
    "continue_unclear": {
        "en": "Please say yes to make another transaction, or end to finish.",
        "ne": "अर्को कारोबार गर्न हो भन्नुहोस्, वा समाप्त गर्न अन्त्य भन्नुहोस्।"},
    "goodbye": {
        "en": "Thank you for using VoiceNPS. Goodbye.",
        "ne": "भ्वाइस एनपीएस प्रयोग गर्नुभएकोमा धन्यवाद। नमस्ते।"},
}

# ------------------------------------------------------------------ words that depend on the language
BANK_NE = {"demo bank": "डेमो बैंक", "sample bank": "स्याम्पल बैंक"}
BILLER_NE = {"electricity": "बिजुली", "internet": "इन्टरनेट", "water": "खानेपानी",
             "mobile topup": "मोबाइल टपअप"}


def num(lang: str, v: float) -> str:
    """2000 -> '2000' | 'दुई हजार'"""
    return f"{v:.0f}" if lang == "en" else number_words_ne(round(v))


def amount(lang: str, v: float) -> str:
    """2000 -> '2000 rupees' | 'दुई हजार रुपैयाँ'"""
    return f"{v:.0f} rupees" if lang == "en" else f"{number_words_ne(round(v))} रुपैयाँ"


def digits(lang: str, s: str) -> str:
    """'0987' -> '0 9 8 7' | 'शून्य नौ आठ सात'"""
    return " ".join(s) if lang == "en" else digits_words_ne(s)


def person(lang: str, name: str, name_ne: str = "") -> str:
    """Full name, in the language's script."""
    return name if lang == "en" else (name_ne or latin_to_devanagari(name))


def masked(lang: str, name: str, name_ne: str = "") -> str:
    """Privacy-friendly: 'Ramesh S.' | first name only in Nepali."""
    if lang == "en":
        parts = name.split()
        return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."
    return (name_ne or latin_to_devanagari(name)).split()[0]


def bank(lang: str, b: str) -> str:
    return b if lang == "en" else BANK_NE.get(b.lower()) or latin_to_devanagari(b)


def biller(lang: str, b: str) -> str:
    return b if lang == "en" else BILLER_NE.get(b.lower()) or latin_to_devanagari(b)


def spoken_name(lang: str, text: str) -> str:
    """Whatever the user said (already Latin after normalising), shown in the reply language."""
    return text if lang == "en" else (NAME_WORDS_NE.get(text.lower()) or latin_to_devanagari(text))


def sep(lang: str) -> str:
    return ". " if lang == "en" else "। "


def render(lang: str, key: str, **kw) -> str:
    entry = MESSAGES[key]
    return entry.get(lang, entry["en"]).format(**kw)
