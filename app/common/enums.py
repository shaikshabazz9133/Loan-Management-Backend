"""Shared enums used across modules."""
from enum import StrEnum


class Role(StrEnum):
    """Every user has exactly one role. It decides which portal they see after login."""

    CUSTOMER = "customer"  # signs up by themselves
    AGENT = "agent"  # created by a manager
    MANAGER = "manager"  # created by scripts/create_manager.py
