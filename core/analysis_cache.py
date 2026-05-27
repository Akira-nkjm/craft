"""Ad-hoc analysis result cache."""

import hashlib
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.paths import analysis_cache_dir
from core.toml_io import read_toml, write_toml_atomic


def cache_dir() -> Path:
    """Backward-compatible alias for `core.paths.analysis_cache_dir`."""
    return analysis_cache_dir()


def code_version_for_func(func: Any) -> str:
    try:
        source = inspect.getsource(func)
    except OSError:
        source = repr(func)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def compute_cache_key(name: str, code_version: str, inputs: dict[str, Any]) -> str:
    """canonicalize(inputs) + code_version の sha256 short hash を返す。"""
    canonical = json.dumps(
        {"name": name, "code_version": code_version, "inputs": inputs},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def get_cached(name: str, key: str) -> dict[str, Any] | None:
    path = cache_dir() / name / f"{key}.toml"
    if not path.exists():
        return None
    return read_toml(path)


def put_cached(name: str, key: str, value_payload: dict[str, Any]) -> Path:
    path = cache_dir() / name / f"{key}.toml"
    payload = {
        "name": name,
        "key": key,
        "cached_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        **value_payload,
    }
    write_toml_atomic(path, payload)
    return path
