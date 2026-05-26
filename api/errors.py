"""RFC 7807 互換エラーレスポンス。

仕様: plan/Craft/最終構成.md §5.4
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError


class ProblemDetails(BaseModel):
    """RFC 7807 problem-details payload。"""

    type: str
    status: int
    title: str
    detail: str | None = None
    errors: list[dict[str, Any]] | None = None
    instance: str | None = None


class CraftAPIError(Exception):
    """Craft API 内で raise する基底例外。"""

    status_code: int = 500
    type_id: str = "internal_error"
    title: str = "Internal server error"

    def __init__(
        self,
        detail: str | None = None,
        *,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        self.errors = errors

    def to_problem(self, instance: str | None = None) -> ProblemDetails:
        return ProblemDetails(
            type=self.type_id,
            status=self.status_code,
            title=self.title,
            detail=self.detail,
            errors=self.errors,
            instance=instance,
        )


class NotFoundError(CraftAPIError):
    status_code = 404
    type_id = "not_found"
    title = "Resource not found"


class ConflictError(CraftAPIError):
    status_code = 409
    type_id = "conflict"
    title = "Resource conflict"


class ETagMismatchError(CraftAPIError):
    status_code = 412
    type_id = "etag_mismatch"
    title = "ETag precondition failed"


class IfMatchRequiredError(CraftAPIError):
    status_code = 428
    type_id = "if_match_required"
    title = "If-Match header required"


class ValidationFailedError(CraftAPIError):
    status_code = 422
    type_id = "validation_error"
    title = "Input validation failed"


def _format_pydantic_errors(exc: ValidationError | RequestValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
            "input": err.get("input"),
        }
        for err in exc.errors()
    ]


def register_exception_handlers(app: FastAPI) -> None:
    """全 endpoint 共通の例外 → RFC 7807 変換を登録。"""

    @app.exception_handler(CraftAPIError)
    async def craft_api_error_handler(request: Request, exc: CraftAPIError) -> JSONResponse:
        problem = exc.to_problem(instance=str(request.url.path))
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(problem.model_dump(exclude_none=True)),
            media_type="application/problem+json",
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        problem = ProblemDetails(
            type="validation_error",
            status=422,
            title="Input validation failed",
            detail=None,
            errors=_format_pydantic_errors(exc),
            instance=str(request.url.path),
        )
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(problem.model_dump(exclude_none=True)),
            media_type="application/problem+json",
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        problem = ProblemDetails(
            type="validation_error",
            status=422,
            title="Input validation failed",
            detail=None,
            errors=_format_pydantic_errors(exc),
            instance=str(request.url.path),
        )
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(problem.model_dump(exclude_none=True)),
            media_type="application/problem+json",
        )
