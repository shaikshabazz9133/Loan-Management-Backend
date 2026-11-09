"""Credit score (simulated bureau), interest-rate pricing and EMI maths.

The frontend never prices a loan itself: it asks POST /eligibility/quote, and POST /applications recalculates
with the same functions before saving, so what the customer sees is exactly what is stored.
"""
from app.core.config import BUSINESS_RULES

# ---------- simulated CIBIL-style bureau (300-900) ----------


def credit_score_for(pan: str) -> int:
    """Sandbox bureau: a random-looking but fixed score per PAN (FNV-1a hash), so it can't be re-rolled.
    About 25% of PANs score below 650. Identical to creditScoreFor() in the frontend's src/lib/kyc.js.
    Replace with the real bureau call when USE_SANDBOX_INTEGRATIONS is false.
    """
    h = 2166136261
    for ch in pan:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return 480 + (h >> 10) % 170 if h % 1000 < 250 else 650 + (h >> 10) % 231


def credit_band(score: int) -> str:
    if score < BUSINESS_RULES["min_credit_score"]:
        return "Poor"
    if score < 700:
        return "Fair"
    if score < 750:
        return "Good"
    return "Excellent"


# ---------- pricing ----------


def _points(value: int, bands: list[dict], key: str) -> int | None:
    for band in bands:
        if key == "min" and value >= band["min"]:
            return band["points"]
        if key == "max" and (band["max"] is None or value <= band["max"]):
            return band["points"]
    return None


def interest_rate_for(credit_score: int, monthly_income: int, tenure_months: int) -> float | None:
    """Rate in % p.a., or None when the credit score is below the minimum (not eligible)."""
    if credit_score < BUSINESS_RULES["min_credit_score"]:
        return None
    pricing = BUSINESS_RULES["pricing"]
    score_points = _points(credit_score, pricing["credit_score_points"], "min")
    if score_points is None:
        return None
    total = (score_points + (_points(monthly_income, pricing["income_points"], "min") or 0)
             + (_points(tenure_months, pricing["tenure_points"], "max") or 0))
    rates = pricing["rates_by_points"]
    return rates[min(total, len(rates) - 1)]


def emi_for(amount: int, tenure_months: int, rate_pa: float) -> int:
    """Reducing-balance EMI: P x r x (1+r)^n / ((1+r)^n - 1), r = monthly rate. Rounded to the rupee."""
    r = rate_pa / 12 / 100
    if r == 0:
        return int(amount / tenure_months + 0.5)
    growth = (1 + r) ** tenure_months
    return int(amount * r * growth / (growth - 1) + 0.5)  # round half up, like JavaScript's Math.round
