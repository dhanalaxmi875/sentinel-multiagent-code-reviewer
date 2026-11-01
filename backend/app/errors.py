from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}


async def api_error_handler(_: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
        headers=error.headers,
    )


async def http_error_handler(_: Request, error: StarletteHTTPException) -> JSONResponse:
    code = "not_found" if error.status_code == 404 else "http_error"
    message = "Not found." if error.status_code == 404 else str(error.detail)
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": code, "message": message}},
        headers=error.headers,
    )


async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    details: list[dict[str, Any]] = error.errors()
    if details:
        item = details[0]
        location = ".".join(str(part) for part in item.get("loc", ()) if part != "body")
        message = str(item.get("msg", "Invalid request."))
        if location:
            message = f"{location}: {message}"
    else:
        message = "Invalid request body."
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": message}},
    )
