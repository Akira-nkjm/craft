"""Write placement edits back to a system's data.toml (comment-preserving).

The marimo viewer (`satellite_viewer.py`) uses this to persist interactive
edits — selecting a component and adjusting its face/side/u/v/w/rz — without
disturbing the surrounding hand-written comments. tomlkit is already a project
dependency, so value updates keep every inline comment intact.

This module is intentionally separate from `satellite_scene.py`, which stays
stdlib-only (read path). Only the write path needs tomlkit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomlkit

EDITABLE_FACES = ("PX", "MX", "PY", "MY", "PZ", "MZ")
EDITABLE_SIDES = ("IN", "OUT")
NUMERIC_FIELDS = ("u", "v", "w", "dx", "dy", "dz", "rz")


def write_placement(
    systems_dir: Path | str,
    system: str,
    path: tuple[str, ...],
    *,
    face: str | None = None,
    side: str | None = None,
    **numeric: float,
) -> Path:
    """Update one placement table in ``systems/<system>/data.toml`` in place.

    ``path`` is the full key path to the placement table as produced by
    ``satellite_scene.PlacementRecord.path`` — e.g.
    ``("reaction_wheels", "main", "design", "placement")``. Only the provided
    fields are touched; comments and unrelated keys are preserved verbatim.
    """

    data_path = Path(systems_dir) / system / "data.toml"
    if not data_path.is_file():
        raise FileNotFoundError(f"data.toml not found: {data_path}")

    doc = tomlkit.parse(data_path.read_text())
    node: Any = doc
    for key in path:
        node = node[key]

    if face is not None:
        if face not in EDITABLE_FACES:
            raise ValueError(f"invalid face: {face!r}; expected one of {EDITABLE_FACES}")
        node["face"] = face
    if side is not None:
        if side not in EDITABLE_SIDES:
            raise ValueError(f"invalid side: {side!r}; expected one of {EDITABLE_SIDES}")
        node["side"] = side
    for key, value in numeric.items():
        if key not in NUMERIC_FIELDS:
            raise ValueError(f"non-editable numeric field: {key!r}")
        node[key] = float(value)

    data_path.write_text(tomlkit.dumps(doc))
    return data_path
