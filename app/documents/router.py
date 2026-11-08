"""Customer document upload and download endpoints."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.core.permissions import require_roles
from app.documents.schemas import DocumentCreated
from app.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["Customer Documents"])
customer_access = Depends(require_roles("customer"))


@router.post("", status_code=201, response_model=DocumentCreated)
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    loan_id: str | None = Form(default=None),
    current_user: dict = customer_access,
):
    """Upload a customer-owned KYC or income document."""
    data = await file.read(5 * 1024 * 1024 + 1)
    document = await DocumentService().upload(
        current_user,
        document_type=document_type,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        content=data,
        loan_id=loan_id,
    )
    return document


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: dict = customer_access,
):
    """Download a document owned by the authenticated customer."""
    document = await DocumentService().get_for_download(
        current_user, document_id
    )
    return Response(
        content=document["content"],
        media_type=document["content_type"],
        headers={
            "Content-Disposition":
                f'attachment; filename="{document["filename"]}"'
        },
    )
