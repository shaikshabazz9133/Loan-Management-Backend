"""M7 Agent Assignments  |  Owner: Manar  |  3 APIs
Area request pool within the agent radius, atomic first-to-accept, decline.

Endpoints to implement (thin handlers -> service layer):
    GET    /api/v1/agent/open-requests                         [Agent]
        Open requests within 2 km of the agent, excluding declined
    POST   /api/v1/applications/{id}/accept                    [Agent]
        Atomic claim - first agent wins (findOneAndUpdate)
    POST   /api/v1/applications/{id}/decline                   [Agent]
        Hide request for this agent (optional reason)
"""
from fastapi import APIRouter

router = APIRouter(tags=["Agent Assignments"])
