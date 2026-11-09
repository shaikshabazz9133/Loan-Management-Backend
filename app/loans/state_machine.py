"""Application status transitions - the single source of truth, enforced server-side.

    unassigned --accept (agent)--> assigned --approve (agent)--> agent_approved --approve (manager)--> approved
                                            --reject  (agent)--> agent_rejected                       --disburse (manager)--> disbursed
    unassigned / assigned / agent_approved --reject (manager)--> rejected

Any active agent can accept an open application; the first one wins. After that only that agent can act on it.
"""
from app.common.enums import Role

UNASSIGNED = "unassigned"
ASSIGNED = "assigned"
AGENT_APPROVED = "agent_approved"
AGENT_REJECTED = "agent_rejected"
APPROVED = "approved"
REJECTED = "rejected"
DISBURSED = "disbursed"

# (action, role) -> (allowed current statuses, new status)
TRANSITIONS: dict[tuple[str, str], tuple[tuple[str, ...], str]] = {
    ("accept", Role.AGENT): ((UNASSIGNED,), ASSIGNED),
    ("approve", Role.AGENT): ((ASSIGNED,), AGENT_APPROVED),
    ("reject", Role.AGENT): ((ASSIGNED,), AGENT_REJECTED),
    ("approve", Role.MANAGER): ((AGENT_APPROVED,), APPROVED),
    ("reject", Role.MANAGER): ((UNASSIGNED, ASSIGNED, AGENT_APPROVED), REJECTED),
    ("disburse", Role.MANAGER): ((APPROVED,), DISBURSED),
}

# Actions an agent can only take on applications they accepted.
AGENT_OWNED_ACTIONS = {"approve", "reject"}

# Shown in history (and on the customer's status page).
HISTORY_ACTION = {
    ("accept", Role.AGENT): "Accepted by agent",
    ("approve", Role.AGENT): "Recommended for approval",
    ("reject", Role.AGENT): "Rejected by agent",
    ("approve", Role.MANAGER): "Loan approved",
    ("reject", Role.MANAGER): "Loan rejected",
    ("disburse", Role.MANAGER): "Amount disbursed",
}
