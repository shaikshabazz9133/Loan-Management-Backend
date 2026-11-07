"""M4 Loan Applications  |  6 APIs
Submit, list and track applications; role-aware responses; timeline, history and the status state machine.

Endpoints to implement (thin handlers -> service layer):
    POST   /api/v1/applications                                [Customer]
        Submit application (KYC, loan, tenure, address, GPS, bank, document ids); Idempotency-Key
    GET    /api/v1/applications                                [Customer, Agent, Manager]  (reusable)
        Role-scoped list with filters, search and pagination
    GET    /api/v1/applications/{id}                           [Customer, Agent, Manager]  (reusable)
        Role-aware detail (agent sees amount/address/location only before accepting)
    GET    /api/v1/applications/{id}/timeline                  [Customer, Agent, Manager]  (reusable)
        6-step progress (submitted -> disbursed)
    GET    /api/v1/applications/{id}/history                   [Customer, Agent, Manager]  (reusable)
        Event log of every action
    POST   /api/v1/applications/{id}/cancel                    [Customer]
        Withdraw before an agent accepts
"""
from fastapi import APIRouter

router = APIRouter(tags=["Loan Applications"])
