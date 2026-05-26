"""MCP surface: convert OperationResult failure to error dict."""

from core.operations import OperationResult


def error_or_none(result: OperationResult) -> dict | None:
    """Return {"error": message} if result.status is not 'ok', else return None."""
    if result.status != "ok":
        return {"error": result.error_message}
    return None
