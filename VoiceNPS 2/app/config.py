"""Central, employer-editable configuration. Override any value with an env var."""
import os

OTP_THRESHOLD_NPR = float(os.getenv("OTP_THRESHOLD_NPR", "500"))  # OTP only when amount >= this
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "120"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
MAX_ACCOUNT_RETRIES = int(os.getenv("MAX_ACCOUNT_RETRIES", "2"))  # auto re-ask before offering retry/cancel
MAX_SINGLE_TRANSFER_NPR = float(os.getenv("MAX_SINGLE_TRANSFER_NPR", "100000"))

# Pluggable back-ends. Employer swaps these for their real implementations.
BANK_ADAPTER = os.getenv("BANK_ADAPTER", "app.adapters.mock:MockBank")
BILLER_ADAPTER = os.getenv("BILLER_ADAPTER", "app.adapters.mock:MockBillers")
OTP_DELIVERY = os.getenv("OTP_DELIVERY", "app.adapters.mock:ConsoleOtpDelivery")
STT_ENGINE = os.getenv("STT_ENGINE", "app.speech:DevSTT")      # or app.speech:WhisperSTT
TTS_ENGINE = os.getenv("TTS_ENGINE", "app.speech:DevTTS")      # or app.speech:Pyttsx3TTS
NLU_ENGINE = os.getenv("NLU_ENGINE", "app.nlu:RuleNLU")        # or app.nlu:LLMNLU
