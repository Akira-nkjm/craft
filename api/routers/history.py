"""GET /history / GET /diff — git log / diff endpoints."""

from typing import Any

from fastapi import APIRouter, Query

from api.errors import CraftAPIError, NotFoundError
from core.history import GitError, GitRefNotFound, git_diff, git_log

router = APIRouter(tags=["history"])


@router.get("/history")
def get_history(
    path: str | None = None,
    limit: int = Query(20, ge=0, le=1000),
) -> dict[str, Any]:
    try:
        entries = git_log(path, limit=limit)
    except GitRefNotFound as e:
        raise NotFoundError(str(e)) from e
    except GitError as e:
        raise CraftAPIError(str(e)) from e

    return {
        "path": path,
        "entries": [
            {
                "sha": entry.sha,
                "author": entry.author,
                "date": entry.date,
                "message": entry.message,
            }
            for entry in entries
        ],
    }


@router.get("/diff")
def get_diff(
    from_sha: str = Query(..., alias="from"),
    to_sha: str = Query(..., alias="to"),
    path: str | None = None,
) -> dict[str, str | None]:
    try:
        diff = git_diff(from_sha, to_sha, path)
    except GitRefNotFound as e:
        raise NotFoundError(str(e)) from e
    except GitError as e:
        raise CraftAPIError(str(e)) from e

    return {
        "from": from_sha,
        "to": to_sha,
        "path": path,
        "diff": diff,
    }
