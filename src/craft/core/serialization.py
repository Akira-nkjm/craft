"""JSON serialization utilities for Craft."""

from pathlib import Path
from typing import Any


def to_jsonable(value: Any, *, allow_callable: bool = False) -> Any:
    """Recursively convert value to a JSON-serializable type.

    - None / bool / int / float / str → returned as-is
    - object with model_dump() (Pydantic BaseModel) → model_dump()
    - dict → {str(k): to_jsonable(v)} recursively
    - list / tuple / set / frozenset → list, recursively converted
    - Path → str
    - type → __name__ or repr
    - callable → repr(value) when allow_callable=True, None otherwise
    - fallback → str(value)
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v, allow_callable=allow_callable) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(v, allow_callable=allow_callable) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, type):
        return getattr(value, "__name__", None) or repr(value)
    if callable(value):
        return repr(value) if allow_callable else None
    return str(value)
