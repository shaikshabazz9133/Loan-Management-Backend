"""What a user document looks like in the MongoDB "users" collection.

Common fields (every role):
    _id, role, name, email, mobile, password_hash, active, created_at, last_login_at
Agent-only fields:
    employee_code ("AG-1001"), area, city, created_by (manager id),
    location: GeoJSON point {"type": "Point", "coordinates": [lng, lat]}   <- MongoDB wants lng first
"""
from datetime import UTC, datetime
from typing import Any

from app.common.enums import Role
from app.core.security import hash_password


def new_user(*, role: Role, name: str, email: str, mobile: str, password: str, active: bool = True,
             **extra: Any) -> dict[str, Any]:
    """Build a user document ready to insert. The plain password is hashed here and never stored."""
    return {
        "role": role.value,
        "name": name,
        "email": email,
        "mobile": mobile,
        "password_hash": hash_password(password),
        "active": active,
        "created_at": datetime.now(UTC),
        "last_login_at": None,
        **extra,
    }


def geo_point(lat: float, lng: float) -> dict[str, Any]:
    return {"type": "Point", "coordinates": [lng, lat]}
