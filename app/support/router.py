"""M14 Support & Health  |  Owner: Soughat  |  2 APIs
Liveness/readiness probes; home for customer help and support tickets.

Endpoints to implement (thin handlers -> service layer):
    GET    /api/v1/health                                      [Public]  (reusable)
        Liveness probe for Docker / load balancer
    GET    /api/v1/health/ready                                [Internal]  (reusable)
        Readiness - checks MongoDB, Redis and object storage
"""
from fastapi import APIRouter

router = APIRouter(tags=["Support & Health"])
