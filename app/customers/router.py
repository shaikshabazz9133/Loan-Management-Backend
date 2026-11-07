"""M3 Customer Management  |  Owner: Shabazz  |  4 APIs
Manager views of customers, their application history, block/unblock.

Endpoints to implement (thin handlers -> service layer):
    GET    /api/v1/customers                                   [Manager]
        Search / filter / paginate customers
    GET    /api/v1/customers/{id}                              [Manager]
        Customer profile and stats
    GET    /api/v1/customers/{id}/applications                 [Manager]
        Customer application history
    PATCH  /api/v1/customers/{id}/status                       [Manager]
        Block / unblock customer
"""
from fastapi import APIRouter

router = APIRouter(tags=["Customer Management"])
