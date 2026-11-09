"""M6 Agent Management

Done:
    POST   /api/v1/agents                       [Manager]  Create agent (credentials, area, location, active)
    GET    /api/v1/agents                       [Manager]  List all agents, newest first
    PATCH  /api/v1/agents/{id}                  [Manager]  Edit agent / change password / activate-deactivate
    DELETE /api/v1/agents/{id}                  [Manager]  Delete agent
    GET    /api/v1/agents/nearby?lat=&lng=      [Customer, Manager]  Active agents within the 2 km radius

To do:
    GET    /api/v1/agents/{id}                  [Manager]  Agent details
    GET    /api/v1/agents/{id}/applications     [Manager]  Applications handled by the agent
    GET    /api/v1/agents/{id}/performance      [Manager]  Performance stats
"""
from fastapi import APIRouter, Depends, Query, status

from app.agents import service
from app.agents.schemas import AgentCreate, AgentUpdate, NearbyAgent
from app.common.enums import Role
from app.core.permissions import require_roles
from app.users.schemas import UserOut

router = APIRouter(prefix="/agents", tags=["Agent Management"])
manager_only = require_roles(Role.MANAGER)


@router.post("", response_model=UserOut, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_agent(data: AgentCreate, manager: dict = Depends(manager_only)) -> UserOut:
    return await service.create_agent(data, manager)


@router.get("", response_model=list[UserOut], response_model_exclude_none=True)
async def list_agents(_: dict = Depends(manager_only)) -> list[UserOut]:
    return await service.list_agents()


@router.get("/nearby", response_model=list[NearbyAgent], response_model_exclude_none=True)
async def nearby(lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180),
                 _: dict = Depends(require_roles(Role.CUSTOMER, Role.MANAGER))) -> list[NearbyAgent]:
    return await service.nearby_agents({"lat": lat, "lng": lng})


@router.patch("/{agent_id}", response_model=UserOut, response_model_exclude_none=True)
async def update_agent(agent_id: str, data: AgentUpdate, _: dict = Depends(manager_only)) -> UserOut:
    return await service.update_agent(agent_id, data)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, _: dict = Depends(manager_only)) -> None:
    await service.delete_agent(agent_id)
