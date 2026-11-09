"""M4 Loan Applications

Public (applicants have no account):
    GET    /api/v1/applications/options                        Apply-form options: purposes, tenures, limits, document rules
    POST   /api/v1/applications                                Submit (multipart: "data" JSON + one file per document type)
    POST   /api/v1/applications/track                          Status for {applicationId, mobile}

Staff:
    GET    /api/v1/applications                                [Agent, Manager]  Agent: open + own; manager: all. Newest first
    POST   /api/v1/applications/{id}/actions                   [Agent, Manager]  accept / approve / reject / disburse
    GET    /api/v1/applications/{id}/documents/{docType}       [Agent, Manager]  View an uploaded file
"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.common.enums import Role
from app.core.config import DOCUMENTS
from app.core.exceptions import Unprocessable
from app.core.permissions import require_roles
from app.loans import service
from app.loans.schemas import (
    ActionRequest, ApplicationCreate, ApplicationOptions, ApplicationOut, SubmitResponse, TrackOut, TrackRequest,
)

router = APIRouter(prefix="/applications", tags=["Loan Applications"])
staff = require_roles(Role.AGENT, Role.MANAGER)


@router.get("/options", response_model=ApplicationOptions, response_model_exclude_none=True)
async def options() -> ApplicationOptions:
    return ApplicationOptions.current()


@router.post("", response_model=SubmitResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED,
             openapi_extra={"requestBody": {"content": {"multipart/form-data": {"schema": {
                 "type": "object", "required": ["data"],
                 "properties": {"data": {"type": "string", "description": "ApplicationCreate as JSON"},
                                **{d["key"]: {"type": "string", "format": "binary"} for d in DOCUMENTS["types"]}},
             }}}}})
async def submit(request: Request) -> SubmitResponse:
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
    return await service.submit(data, files)


@router.post("/track", response_model=TrackOut, response_model_exclude_none=True)
async def track(data: TrackRequest) -> TrackOut:
    """POST (not GET) so the mobile number stays out of URLs and logs."""
    return await service.track(data)


@router.get("", response_model=list[ApplicationOut], response_model_exclude_none=True)
async def list_applications(user: dict = Depends(staff)) -> list[ApplicationOut]:
    return await service.list_for(user)


@router.post("/{application_id}/actions", response_model=ApplicationOut, response_model_exclude_none=True)
async def act(application_id: str, data: ActionRequest, user: dict = Depends(staff)) -> ApplicationOut:
    return await service.act(application_id, data, user)


@router.get("/{application_id}/documents/{doc_type}", response_class=Response)
async def get_document(application_id: str, doc_type: str, user: dict = Depends(staff)) -> Response:
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
