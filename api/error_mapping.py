"""OperationResult → FastAPI HTTP exceptions."""

from fastapi import Response
from pydantic import ValidationError as PydanticValidationError

from api.errors import (
    ConflictError,
    ETagMismatchError,
    IfMatchRequiredError,
    NotFoundError,
    ValidationFailedError,
)
from core.operations import OperationResult


def apply_api_result(result: OperationResult, response: Response | None = None) -> None:
    """Raise appropriate HTTP exception for non-ok results; set ETag header on success."""
    if result.status == "ok":
        if response is not None and result.etag is not None:
            response.headers["ETag"] = result.etag
        return
    if result.status == "not_found":
        raise NotFoundError(result.error_code)
    if result.status == "conflict":
        raise ConflictError(result.error_code)
    if result.status == "validation":
        # Re-raise the original Pydantic error so the global handler can add structured errors.
        if isinstance(result.exc, PydanticValidationError):
            raise result.exc
        raise ValidationFailedError(result.error_code)
    if result.status == "etag_mismatch":
        raise ETagMismatchError(result.error_code)
    raise IfMatchRequiredError(result.error_code)
