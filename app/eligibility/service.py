"""Loan quote shown on the apply form (same maths POST /applications uses when it saves the application)."""
from app.core.config import BUSINESS_RULES
from app.eligibility.emi import credit_band, credit_score_for, emi_for, interest_rate_for
from app.eligibility.schemas import QuoteOut, QuoteRequest


def quote(data: QuoteRequest) -> QuoteOut:
    score = credit_score_for(data.pan)
    minimum = BUSINESS_RULES["min_credit_score"]
    result = QuoteOut(credit_score=score, credit_band=credit_band(score), eligible=score >= minimum,
                      min_credit_score=minimum)
    if result.eligible and data.amount and data.income and data.tenure:
        rate = interest_rate_for(score, data.income, data.tenure)
        emi = emi_for(data.amount, data.tenure, rate)
        result.rate_pa = rate
        result.emi = emi
        result.total_payable = emi * data.tenure
        result.total_interest = emi * data.tenure - data.amount
    return result
