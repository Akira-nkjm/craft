"""ETag concurrency policy shared across CLI, MCP, and API surfaces.

All write surfaces (CLI, MCP, API) should use resolve_expected_etag to apply
a consistent optimistic-locking policy rather than each surface implementing
its own ad-hoc ETag resolution logic.
"""

from collections.abc import Callable
from typing import Literal

from craft.core.errors import PreconditionRequired

ETagMode = Literal["required", "auto"]


def resolve_expected_etag(
    provided: str | None,
    mode: ETagMode,
    *,
    fetch: Callable[[], str],
) -> str:
    """Return the ETag to use for an optimistic-lock write operation.

    provided: caller-supplied ETag (from --etag / payload field / HTTP header)
    mode:     "required" raises PreconditionRequired when provided is None
              "auto"     fetches the current ETag via fetch() when provided is None
    fetch:    zero-arg callable that returns the current resource ETag;
              only called when mode is "auto" and provided is None

    Raises:
        PreconditionRequired: when mode is "required" and provided is None
        Any exception from fetch(): propagated unchanged (e.g. InstanceNotFound)
    """
    if provided is not None:
        return provided
    if mode == "auto":
        return fetch()
    raise PreconditionRequired(
        "ETag is required for this operation. "
        "Supply the current resource ETag, or use --auto-etag to fetch it automatically "
        "(note: --auto-etag disables optimistic concurrency protection)."
    )
