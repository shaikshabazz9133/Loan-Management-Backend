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
