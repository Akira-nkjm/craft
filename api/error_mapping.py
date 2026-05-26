"""API surface: convert OperationResult to HTTP responses or CraftAPIError."""

from typing import Any

from fastapi import Response

from api.errors import (
    ConflictError,
    ETagMismatchError,
    IfMatchRequiredError,
    NotFoundError,
    ValidationFailedError,
)
from core.operations import OperationResult


def raise_for_error(result: OperationResult) -> None:
    """Raise the appropriate CraftAPIError if result.status is not 'ok'."""
    if result.status == "ok":
        return
    if result.status == "not_found":
        raise NotFoundError(result.error_message)
    if result.status == "conflict":
        raise ConflictError(result.error_message)
    if result.status == "etag_mismatch":
        raise ETagMismatchError(result.error_message)
    if result.status == "precondition":
        raise IfMatchRequiredError(result.error_message)
    raise ValidationFailedError(result.error_message)


def raise_for_result(result: OperationResult, response: Response | None = None) -> Any:
    """For write ops that return a payload: raise on failure, set ETag header, return payload."""
    raise_for_error(result)
    if response is not None and result.etag is not None:
        response.headers["ETag"] = result.etag
    return result.payload
