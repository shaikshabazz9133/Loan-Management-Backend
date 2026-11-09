"""Agent management. Only managers create agents; an agent then signs in with POST /auth/login."""
from datetime import UTC, datetime

from app.agents.schemas import AgentCreate, AgentUpdate
from app.common.enums import Role
from app.core.exceptions import Conflict, NotFound
from app.loans import repository as loans_repository
from app.core.security import hash_password
from app.users import repository as users_repository
from app.users.models import geo_point, new_user
from app.users.schemas import UserOut
from app.users.service import ensure_email_and_mobile_free


async def create_agent(data: AgentCreate, manager: dict) -> UserOut:
    await ensure_email_and_mobile_free(data.email, data.mobile)
    number = await users_repository.next_sequence("agent_code")
    agent = await users_repository.insert(new_user(
        role=Role.AGENT,
        name=data.name,
        email=data.email,
        mobile=data.mobile,
        password=data.password,
        active=data.active,
        employee_code=f"AG-{1000 + number}",  # AG-1001, AG-1002, ...
        area=data.area,
        city=data.city,
        location=geo_point(data.location.lat, data.location.lng) if data.location else None,
        created_by=manager["_id"],
    ))
    return UserOut.from_doc(agent)


async def list_agents() -> list[UserOut]:
    return [UserOut.from_doc(doc) for doc in await users_repository.list_by_role(Role.AGENT)]


async def _get_agent(agent_id: str) -> dict:
    agent = await users_repository.find_by_id(agent_id)
    if agent is None or agent["role"] != Role.AGENT:
        raise NotFound("AGENT_NOT_FOUND", "Agent not found.")
    return agent


async def update_agent(agent_id: str, data: AgentUpdate) -> UserOut:
    """Edit details, change password, or activate/deactivate (deactivated agents are signed out at once)."""
    agent = await _get_agent(agent_id)
    changes = data.model_dump(exclude_none=True)
    await ensure_email_and_mobile_free(changes.get("email"), changes.get("mobile"), except_id=agent["_id"])
    if "password" in changes:
        changes["password_hash"] = hash_password(changes.pop("password"))
    if "location" in changes:
        location = changes.pop("location")
        changes["location"] = geo_point(location["lat"], location["lng"])
    changes["updated_at"] = datetime.now(UTC)
    updated = await users_repository.update(agent["_id"], changes)
    if data.active is False:
        await loans_repository.release_agent_applications(agent["_id"], changes["updated_at"])
    return UserOut.from_doc(updated)


async def delete_agent(agent_id: str) -> None:
    agent = await _get_agent(agent_id)
    if await loans_repository.count({"agent_id": agent["_id"]}):
        raise Conflict("AGENT_HAS_APPLICATIONS",
                       "This agent has applications. Deactivate the agent instead so their history is kept.")
    await users_repository.delete(agent["_id"])

