"""Customer management. Customers are users with role "customer" (created by POST /auth/register)."""
from app.common.enums import Role
from app.users import repository as users_repository
from app.users.schemas import UserOut


async def list_customers() -> list[UserOut]:
    return [UserOut.from_doc(doc) for doc in await users_repository.list_by_role(Role.CUSTOMER)]
