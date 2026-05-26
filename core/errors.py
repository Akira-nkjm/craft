"""Core exception hierarchy for Craft.

These exceptions are raised by core/ modules and must not import from api/.
"""


class CraftError(Exception):
    """Base exception for all Craft errors."""


class PreconditionRequired(CraftError):  # noqa: N818
    """If-Match header is required but was not provided."""


class ETagMismatch(CraftError):  # noqa: N818
    """If-Match header did not match the current ETag."""


class ResourceNotFound(CraftError):  # noqa: N818
    """Requested resource does not exist."""


class ResourceConflict(CraftError):  # noqa: N818
    """Resource already exists or conflicts with existing state."""


class AnalysisNotFound(CraftError):  # noqa: N818
    """Requested analysis is not registered."""


class AnalysisArgumentError(CraftError):
    """Payload does not match the analysis function signature."""
