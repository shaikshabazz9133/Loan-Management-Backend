"""Errors and the handlers that turn them into one consistent JSON body:

    {"error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect email/mobile or password."}}

Validation errors also include "details": {"fieldName": "message"} so the frontend can show them under each field.
In services, just `raise Conflict("EMAIL_TAKEN", "...")` - never build HTTP responses by hand.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, code: str, message: str, details: dict[str, str] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details  # optional {"fieldName": "message"} shown under form fields


class BadRequest(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class Unauthorized(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED


class Forbidden(AppError):
    status_code = status.HTTP_403_FORBIDDEN


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class Conflict(AppError):
    status_code = status.HTTP_409_CONFLICT


class Unprocessable(AppError):
    """Input that passed the schema but breaks a rule, e.g. a missing document. Pass details for per-field messages."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


def _error(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    body: dict = {"code": code, "message": message}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status_code, content={"error": body})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict[str, str] = {}
        for err in exc.errors():
            field = str(err["loc"][-1]) if err["loc"] else "body"
            details.setdefault(field, err["msg"].removeprefix("Value error, "))
        first = next(iter(details.values()), "Invalid request.")
        return _error(422, "VALIDATION_ERROR", first, details)
