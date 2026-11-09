"""M4 Loan Applications

Done:
    GET    /api/v1/applications/options                        [Any]       Apply-form options: purposes, tenures, limits, document rules
    POST   /api/v1/applications                                [Customer]  Submit (multipart: "data" JSON + one file per document type)
    GET    /api/v1/applications                                [Customer, Agent, Manager]  Role-scoped list, newest first
    GET    /api/v1/applications/{id}/documents/{docType}       [Customer (own), Agent (in area), Manager]  View an uploaded file

To do (agent/manager workflow is still in the frontend's local store):
    accept / decline / verify / recommend / approve / reject / disburse
"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.common.enums import Role
from app.core.config import DOCUMENTS
from app.core.deps import get_current_user
from app.core.exceptions import Unprocessable
from app.core.permissions import require_roles
from app.loans import service
from app.loans.schemas import ApplicationCreate, ApplicationOptions, ApplicationOut, SubmitResponse

router = APIRouter(prefix="/applications", tags=["Loan Applications"])


@router.get("/options", response_model=ApplicationOptions, response_model_exclude_none=True)
async def options(_: dict = Depends(get_current_user)) -> ApplicationOptions:
    return ApplicationOptions.current()


@router.post("", response_model=SubmitResponse, status_code=status.HTTP_201_CREATED,
             openapi_extra={"requestBody": {"content": {"multipart/form-data": {"schema": {
                 "type": "object", "required": ["data"],
                 "properties": {"data": {"type": "string", "description": "ApplicationCreate as JSON"},
                                **{d["key"]: {"type": "string", "format": "binary"} for d in DOCUMENTS["types"]}},
             }}}}})
async def submit(request: Request, customer: dict = Depends(require_roles(Role.CUSTOMER))) -> SubmitResponse:
    """One request carries the form and every document, so a half-submitted application can't exist."""
    form = await request.form()
    raw = form.get("data")
    if not isinstance(raw, str):
        raise Unprocessable("VALIDATION_ERROR", "Application details are missing.")
    try:
        data = ApplicationCreate.model_validate_json(raw)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None
    files = {key: value for key, value in form.multi_items() if isinstance(value, UploadFile)}
    return await service.submit(data, files, customer)


@router.get("", response_model=list[ApplicationOut], response_model_exclude_none=True)
async def list_applications(user: dict = Depends(get_current_user)) -> list[ApplicationOut]:
    return await service.list_for(user)


@router.get("/{application_id}/documents/{doc_type}", response_class=Response)
async def get_document(application_id: str, doc_type: str, user: dict = Depends(get_current_user)) -> Response:
    stored = await service.get_document(application_id, doc_type, user)
    return Response(
        content=bytes(stored["data"]),
        media_type=stored["content_type"],
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(stored['name'])}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
