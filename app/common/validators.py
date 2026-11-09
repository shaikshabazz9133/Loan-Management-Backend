"""Small input helpers shared by several modules."""
import re

_MOBILE = re.compile(r"^[6-9]\d{9}$")  # Indian mobile: 10 digits starting with 6-9


def normalize_mobile(value: str) -> str:
    """'+91 98765 43210' -> '9876543210'. Raises ValueError if it is not a valid Indian mobile number."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if not _MOBILE.match(digits):
        raise ValueError("Enter a valid 10-digit mobile number.")
    return digits


def normalize_email(value: str) -> str:
    return value.strip().lower()


def looks_like_email(value: str) -> bool:
    return "@" in value


# ---------- KYC & bank (same rules as the frontend's src/lib/kyc.js and src/lib/bank.js) ----------
_PAN = re.compile(r"^[A-Z]{3}P[A-Z]\d{4}[A-Z]$")  # 4th letter "P" = individual
_IFSC = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_ACCOUNT = re.compile(r"^\d{9,18}$")
_AADHAAR = re.compile(r"^[2-9]\d{11}$")

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 1, 0],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_BANKS = {
    "SBIN": "State Bank of India", "HDFC": "HDFC Bank", "ICIC": "ICICI Bank", "UTIB": "Axis Bank",
    "KKBK": "Kotak Mahindra Bank", "PUNB": "Punjab National Bank", "BARB": "Bank of Baroda", "CNRB": "Canara Bank",
    "UBIN": "Union Bank of India", "IDIB": "Indian Bank", "YESB": "Yes Bank", "INDB": "IndusInd Bank",
    "IDFB": "IDFC FIRST Bank", "FDRL": "Federal Bank", "BKID": "Bank of India", "IOBA": "Indian Overseas Bank",
}


def verhoeff_valid(digits: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def normalize_aadhaar(value: str, *, demo_mode: bool = False) -> str:
    """12 digits, first digit 2-9, valid UIDAI check digit (checksum skipped in demo mode)."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 12:
        raise ValueError("Aadhaar numbers have 12 digits.")
    if not _AADHAAR.match(digits):
        raise ValueError("Aadhaar numbers never start with 0 or 1.")
    if not demo_mode and not verhoeff_valid(digits):
        raise ValueError("This Aadhaar number fails the UIDAI check-digit test. Please check it.")
    return digits


def normalize_pan(value: str) -> str:
    pan = (value or "").strip().upper()
    if not _PAN.match(pan):
        raise ValueError("Enter a valid individual PAN, e.g. ABCPK1234D (4th letter is P).")
    return pan


def normalize_ifsc(value: str) -> str:
    ifsc = (value or "").strip().upper()
    if not _IFSC.match(ifsc):
        raise ValueError("Enter a valid IFSC, e.g. HDFC0001234.")
    return ifsc


def normalize_account_number(value: str) -> str:
    digits = (value or "").strip()
    if not _ACCOUNT.match(digits):
        raise ValueError("Enter a valid account number (9-18 digits).")
    return digits


def bank_name_from_ifsc(ifsc: str) -> str:
    return _BANKS.get(ifsc[:4], f"{ifsc[:4]} Bank")
