"""History MCP tool handlers."""

from typing import Any

from craft.core.persistence.history import (
    GitError,
    GitRefNotFound,
    git_diff,
    git_log,
)


def handle_history(payload: dict[str, Any]) -> Any:
    path = payload.get("path")
    limit_raw = payload.get("limit", 20)
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        return {"error": "limit must be an integer"}
    try:
        entries = git_log(path, limit=limit)
    except GitRefNotFound as e:
        return {"error": f"ref_not_found: {e}"}
    except GitError as e:
        return {"error": f"git_error: {e}"}
    return {
        "path": path,
        "entries": [
            {"sha": e.sha, "author": e.author, "date": e.date, "message": e.message}
            for e in entries
        ],
    }


def handle_diff(payload: dict[str, Any]) -> Any:
    from_sha = payload.get("from")
    to_sha = payload.get("to")
    if not from_sha or not to_sha:
        return {"error": "from and to are required"}
    path = payload.get("path")
    try:
        diff_text = git_diff(from_sha, to_sha, path)
    except GitRefNotFound as e:
        return {"error": f"ref_not_found: {e}"}
    except GitError as e:
        return {"error": f"git_error: {e}"}
    return {"from": from_sha, "to": to_sha, "path": path, "diff": diff_text}
