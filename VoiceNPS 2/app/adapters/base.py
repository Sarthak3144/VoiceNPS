"""Interfaces the employer implements to plug in their own bank / biller / SMS systems."""
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class AccountInfo:
    account_no: str
    holder_name: str      # full name stays server-side; only a masked form is ever spoken
    bank: str
    name_ne: str = ""     # optional Devanagari spelling (used for Nepali replies)


@dataclass
class Contact:
    name: str             # the name the user saved, e.g. "Ramesh Sharma"
    account_no: str
    bank: str
    name_ne: str = ""     # optional Devanagari spelling, e.g. "रमेश शर्मा"


@dataclass
class BillInfo:
    biller: str
    customer_id: str
    customer_name: str
    amount_due: float
    name_ne: str = ""


@dataclass
class TxResult:
    ok: bool
    reference: str = ""
    reason: str = ""


class BankAdapter(Protocol):
    def validate_account(self, account_no: str) -> Optional[AccountInfo]: ...
    def transfer(self, user_id: str, to_account: str, amount: float, idem_key: str) -> TxResult: ...
    def source_account(self, user_id: str) -> Optional[AccountInfo]: ...
    def contacts(self, user_id: str) -> list[Contact]: ...   # the user's saved beneficiaries


class BillerAdapter(Protocol):
    def list_billers(self) -> list[str]: ...
    def lookup_bill(self, biller: str, customer_id: str) -> Optional[BillInfo]: ...
    def pay_bill(self, user_id: str, biller: str, customer_id: str, amount: float, idem_key: str) -> TxResult: ...


class OtpDelivery(Protocol):
    def send(self, user_id: str, otp: str) -> None: ...
