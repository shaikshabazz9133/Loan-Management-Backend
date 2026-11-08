"""Schemas for customer documents."""

from datetime import datetime
from pydantic import BaseModel


class DocumentCreated(BaseModel):
    id: str
    loan_id: str | None
    document_type: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
