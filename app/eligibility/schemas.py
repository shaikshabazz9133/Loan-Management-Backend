"""Loan quote: credit score + interest rate + EMI for the apply form."""
from pydantic import Field, field_validator

from app.common.responses import CamelModel
from app.common.validators import normalize_pan


class QuoteRequest(CamelModel):
    """PAN alone returns just the credit score; add amount, income and tenure to get the rate and EMI too."""

    pan: str
    amount: int | None = Field(default=None, gt=0)
    income: int | None = Field(default=None, gt=0)
    tenure: int | None = Field(default=None, gt=0)

    @field_validator("pan")
    @classmethod
    def _pan(cls, v: str) -> str:
        return normalize_pan(v)


class QuoteOut(CamelModel):
    credit_score: int
    credit_band: str  # Poor / Fair / Good / Excellent
    eligible: bool  # False when the score is below min_credit_score
    min_credit_score: int
    # present once amount, income and tenure are sent (and the customer is eligible)
    rate_pa: float | None = None
    emi: int | None = None
    total_interest: int | None = None
    total_payable: int | None = None
