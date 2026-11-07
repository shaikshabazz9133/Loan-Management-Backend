"""M6 Agent Management  |  Owner: Manar  |  9 APIs
Manager CRUD for agents including GeoJSON location; geo search of nearby agents.

Endpoints to implement (thin handlers -> service layer):
    POST   /api/v1/agents                                      [Manager]
        Create agent with location (lat/lng), area and credentials
    GET    /api/v1/agents                                      [Manager]
        List / search / filter (active, area)
    GET    /api/v1/agents/{id}                                 [Manager]
        Agent details
    PATCH  /api/v1/agents/{id}                                 [Manager]
        Edit agent incl. location
    PATCH  /api/v1/agents/{id}/status                          [Manager]
        Activate / deactivate; releases unfinished cases to the open pool
    DELETE /api/v1/agents/{id}                                 [Manager]
        Soft delete (blocked if applications exist)
    GET    /api/v1/agents/{id}/applications                    [Manager]
        Customers / applications handled by the agent
    GET    /api/v1/agents/{id}/performance                     [Manager]
        Processed, recommendation rate, manager agreement
    GET    /api/v1/agents/nearby                               [Customer, Manager]  (reusable)
        Active agents within radius of lat/lng (2dsphere)
"""
from fastapi import APIRouter

router = APIRouter(tags=["Agent Management"])
