"""The one error shape every non-2xx response uses (docs/lanes/vp.md:
"One error body everywhere: code, message, detail").

FastAPI's default `HTTPException` nests whatever you pass under a top-level
`"detail"` key (`{"detail": ...}`), which is not this shape. `ApiError` plus
the handlers registered in `register_exception_handlers` make every error
path — a route raising deliberately, a role check failing, a 404, even
FastAPI's own request-validation failures — come back as exactly
`{"code": ..., "message": ..., "detail": ...}` at the top level.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.envelope import ErrorBody

# Reusable `responses=` fragments for route decorators, so the declared error
# shape shows up in the generated OpenAPI schema (and therefore in Adhya's
# generated types) rather than only existing as runtime behavior.
NOT_FOUND_RESPONSE = {404: {"model": ErrorBody, "description": "No resource with that id."}}
FORBIDDEN_RESPONSE = {
    403: {"model": ErrorBody, "description": "The current role may not perform this action."}
}
CONFLICT_RESPONSE = {
    409: {"model": ErrorBody, "description": "The resource is not in a state this action applies to."}
}
SERVICE_UNAVAILABLE_RESPONSE = {
    503: {
        "model": ErrorBody,
        "description": "A downstream dependency (e.g. governance) could not serve this request.",
    }
}


class ApiError(Exception):
    """Raise this, not `HTTPException`, everywhere in `app/api/v1/`."""

    def __init__(self, status_code: int, code: str, message: str, detail: object | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


def not_found(code: str, message: str, detail: object | None = None) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, code, message, detail)


def service_unavailable(code: str, message: str, detail: object | None = None) -> ApiError:
    return ApiError(status.HTTP_503_SERVICE_UNAVAILABLE, code, message, detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorBody(code=exc.code, message=exc.message, detail=exc.detail).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        # `exc.detail` may already be an ErrorBody-shaped dict (app/deps.py raises
        # HTTPException with one, since Depends() can't raise ApiError directly and
        # be caught by FastAPI's dependency-resolution exception path the same way);
        # otherwise wrap Starlette's own detail (e.g. its stock 404) into the shape.
        if isinstance(exc.detail, dict) and {"code", "message"} <= exc.detail.keys():
            body = exc.detail
        else:
            body = ErrorBody(code="http_error", message=str(exc.detail), detail=None).model_dump()
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=ErrorBody(
                code="validation_error",
                message="Request failed validation.",
                detail=exc.errors(),
            ).model_dump(),
        )
