"""OperationResult → MCP error dict."""

from typing import Any

from core.operations import OperationResult


def mcp_error(result: OperationResult) -> dict[str, Any] | None:
    """Return {"error": message} for non-ok results, or None on success."""
    if result.status == "ok":
        return None
    return {"error": result.error_code}
