"""Document upload/download rules and ownership checks."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId
from fastapi import HTTPException

from app.core.config import DOCUMENTS
from app.documents.repository import DocumentRepository
from app.loans.service import LoanService


def _customer_id(current_user: dict) -> str:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid customer token")
    return str(user_id)


class DocumentService:
    def __init__(self) -> None:
        self.repository = DocumentRepository()

    async def upload(
        self,
        current_user: dict,
        *,
        document_type: str,
        filename: str,
        content_type: str,
        content: bytes,
        loan_id: str | None,
    ) -> dict[str, Any]:
        customer_id = _customer_id(current_user)
        max_bytes = int(DOCUMENTS.get("max_size_mb", 5)) * 1024 * 1024
        allowed_types = set(DOCUMENTS.get("allowed_mime_types", []))

        if len(content) > max_bytes:
            raise HTTPException(status_code=413, detail="File exceeds the size limit")
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        if content_type not in allowed_types:
            raise HTTPException(status_code=415, detail="Unsupported document type")
        if not document_type.strip():
            raise HTTPException(status_code=422, detail="document_type is required")

        if loan_id is not None:
            await LoanService().get_application(current_user, loan_id)

        now = datetime.now(timezone.utc)
        record = {
            "customer_id": customer_id,
            "loan_id": loan_id,
            "document_type": document_type.strip().lower(),
            "filename": Path(filename).name,
            "content_type": content_type,
            "size_bytes": len(content),
            "content": content,
            "created_at": now,
        }
        inserted_id = await self.repository.insert(record)
        return {
            "id": str(inserted_id),
            "loan_id": loan_id,
            "document_type": record["document_type"],
            "filename": record["filename"],
            "content_type": content_type,
            "size_bytes": len(content),
            "created_at": now,
        }

    async def get_for_download(
        self, current_user: dict, document_id: str
    ) -> dict[str, Any]:
        if not ObjectId.is_valid(document_id):
            raise HTTPException(status_code=404, detail="Document not found")
        record = await self.repository.find_owned(
            ObjectId(document_id), _customer_id(current_user)
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return record
