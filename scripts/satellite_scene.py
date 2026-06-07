"""Build Plotly satellite box scenes from systems/*/data.toml placement tables.

Coordinate convention:
- Body axes are X, Y, Z. The origin is the envelope center. Units are mm.
- PX/MX, PY/MY, PZ/MZ map to normal axes X, Y, Z with signs +/-.
- C and cylindrical faces CY+/CY-/CX+/CX-/CZ+/CZ- are placed at the body
  center; normal handling is skipped and u/v/w are treated as zero.
- Box size is (dx, dy, dz).
- For a normal face, center[n] = s * L[n] / 2 + dir * (w + t / 2), where
  t is the box thickness on the normal axis and dir is outward for side OUT,
  inward for side IN. The remaining two body axes receive u and v in X<Y<Z
  order as offsets from the face center.
- rz is a yaw rotation around the face normal.

This module intentionally reads TOML with the standard library only. It does
not import craft or veriq and does not require merged TOML output.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any, Literal

import plotly.graph_objects as go

type Axis = Literal["X", "Y", "Z"]
type Face = Literal[
    "PX",
    "MX",
    "PY",
    "MY",
    "PZ",
    "MZ",
    "C",
    "CY+",
    "CY-",
    "CX+",
    "CX-",
    "CZ+",
    "CZ-",
]
type Vec3 = tuple[float, float, float]

AXES: tuple[Axis, Axis, Axis] = ("X", "Y", "Z")
DIM_KEYS = ("dx", "dy", "dz")
PLACEMENT_NUMERIC_KEYS = ("u", "v", "w", "dx", "dy", "dz", "rz")
SYSTEM_PALETTE: dict[str, str] = {
    "aocs": "#e15759",
    "cdh": "#4e79a7",
    "comm": "#f28e2b",
    "mission": "#59a14f",
    "orbital": "#b07aa1",
    "power": "#edc948",
    "structure": "#bab0ac",
    "thermal": "#76b7b2",
}
FACE_NORMALS: dict[Face, tuple[int, int] | None] = {
    "PX": (0, 1),
    "MX": (0, -1),
    "PY": (1, 1),
    "MY": (1, -1),
    "PZ": (2, 1),
    "MZ": (2, -1),
    "C": None,
    "CY+": None,
    "CY-": None,
    "CX+": None,
    "CX-": None,
    "CZ+": None,
    "CZ-": None,
}
MESH_I = (0, 0, 4, 4, 0, 0, 3, 3, 0, 0, 1, 1)
MESH_J = (1, 2, 6, 7, 5, 4, 2, 6, 3, 7, 5, 6)
MESH_K = (2, 3, 5, 6, 1, 5, 6, 7, 7, 4, 6, 2)
ENVELOPE_EDGE_INDEXES = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 0),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 4),
    (0, 4),
    (1, 5),
    (2, 6),
    (3, 7),
)


@dataclass(frozen=True)
class PlacementRecord:
    """A normalized placement record found in one systems/*/data.toml file."""

    system: str
    name: str
    path: tuple[str, ...]
    face: Face
    u: float
    v: float
    w: float
    size: Vec3
    rz: float
    side: Literal["IN", "OUT"]


def build_scene(systems_dir: Path) -> tuple[list[PlacementRecord], Vec3]:
    """Load placement records and derive the spacecraft envelope."""

    placements = load_placements(systems_dir)
    return placements, compute_envelope(placements)


def load_placements(systems_dir: Path) -> list[PlacementRecord]:
    if not systems_dir.exists():
        raise FileNotFoundError(f"systems directory not found: {systems_dir}")

    placements: list[PlacementRecord] = []
    for data_path in sorted(systems_dir.glob("*/data.toml")):
        placements.extend(load_system_placements(data_path, data_path.parent.name))
    return placements


def load_system_placements(data_path: Path, system: str) -> list[PlacementRecord]:
    try:
        with data_path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"failed to parse TOML: {data_path}: {exc}") from exc

    return collect_placements(data, system, ())


def collect_placements(node: Any, system: str, path: tuple[str, ...]) -> list[PlacementRecord]:
    if not isinstance(node, dict):
        return []
    if is_placement_table(node):
        return [parse_placement(node, system, path)]

    placements: list[PlacementRecord] = []
    for key, value in node.items():
        placements.extend(collect_placements(value, system, (*path, str(key))))
    return placements


def is_placement_table(node: dict[str, Any]) -> bool:
    return "face" in node and any(key in node for key in DIM_KEYS)


def parse_placement(node: dict[str, Any], system: str, path: tuple[str, ...]) -> PlacementRecord:
    path_text = ".".join(path) or "<root>"
    face = parse_face(node.get("face"), path_text)
    side = parse_side(node.get("side", "IN"), path_text)
    values = {
        key: parse_float(node.get(key, 0.0), key, path_text) for key in PLACEMENT_NUMERIC_KEYS
    }
    validate_dimensions(values["dx"], values["dy"], values["dz"], path_text)

    return PlacementRecord(
        system=system,
        name=component_name(path),
        path=path,
        face=face,
        u=values["u"],
        v=values["v"],
        w=values["w"],
        size=(values["dx"], values["dy"], values["dz"]),
        rz=values["rz"],
        side=side,
    )


def parse_face(value: Any, path_text: str) -> Face:
    if not isinstance(value, str) or value not in FACE_NORMALS:
        allowed = ", ".join(FACE_NORMALS)
        raise ValueError(
            f"invalid placement face at {path_text}: {value!r}; expected one of {allowed}"
        )
    return value


def parse_side(value: Any, path_text: str) -> Literal["IN", "OUT"]:
    if not isinstance(value, str) or value not in {"IN", "OUT"}:
        raise ValueError(f"invalid placement side at {path_text}: {value!r}; expected IN or OUT")
    return value


def parse_float(value: Any, key: str, path_text: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"invalid numeric placement field {path_text}.{key}: {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite placement field {path_text}.{key}: {value!r}")
    return number


def validate_dimensions(dx: float, dy: float, dz: float, path_text: str) -> None:
    if min(dx, dy, dz) < 0.0:
        raise ValueError(f"negative placement dimension at {path_text}: {(dx, dy, dz)!r}")


def component_name(path: tuple[str, ...]) -> str:
    parts = list(path)
    if len(parts) >= 2 and parts[-2:] == ["design", "placement"]:
        parts = parts[:-2]
    elif parts and parts[-1] == "placement":
        parts = parts[:-1]
    return ".".join(parts) or "<root>"


def compute_envelope(placements: list[PlacementRecord]) -> Vec3:
    frame_sizes = [
        record.size
        for record in placements
        if record.system == "structure" and any(part == "frames" for part in record.path)
    ]
    if frame_sizes:
        envelope = max_components(frame_sizes)
        if max(envelope) > 0.0:
            return envelope
    return fallback_envelope(placements)


def fallback_envelope(placements: list[PlacementRecord]) -> Vec3:
    if not placements:
        return (1.0, 1.0, 1.0)

    raw_seed = max_components(record.size for record in placements)
    seed: Vec3 = (max(raw_seed[0], 1.0), max(raw_seed[1], 1.0), max(raw_seed[2], 1.0))
    centers = [box_center(record, seed) for record in placements]

    lows = [math.inf, math.inf, math.inf]
    highs = [-math.inf, -math.inf, -math.inf]
    for record, center in zip(placements, centers, strict=True):
        for index, size in enumerate(record.size):
            lows[index] = min(lows[index], center[index] - size / 2.0)
            highs[index] = max(highs[index], center[index] + size / 2.0)

    return (
        max(highs[0] - lows[0], seed[0], 1.0),
        max(highs[1] - lows[1], seed[1], 1.0),
        max(highs[2] - lows[2], seed[2], 1.0),
    )


def max_components(vectors: Any) -> Vec3:
    maxima = [0.0, 0.0, 0.0]
    for vector in vectors:
        for index, value in enumerate(vector):
            maxima[index] = max(maxima[index], float(value))
    return (maxima[0], maxima[1], maxima[2])


def box_center(record: PlacementRecord, envelope: Vec3) -> Vec3:
    normal = FACE_NORMALS[record.face]
    if normal is None:
        return (0.0, 0.0, 0.0)

    axis_index, sign = normal
    center = [0.0, 0.0, 0.0]
    thickness = record.size[axis_index]
    direction = sign if record.side == "OUT" else -sign
    center[axis_index] = sign * envelope[axis_index] / 2.0
    center[axis_index] += direction * (record.w + thickness / 2.0)

    in_plane_axes = [index for index in range(3) if index != axis_index]
    center[in_plane_axes[0]] = record.u
    center[in_plane_axes[1]] = record.v
    return (center[0], center[1], center[2])


def is_envelope_sized(size: Vec3, envelope: Vec3) -> bool:
    covered_axes = 0
    for box_dim, env_dim in zip(size, envelope, strict=True):
        if env_dim > 0.0 and box_dim >= env_dim * 0.9:
            covered_axes += 1
    return covered_axes >= 2


def is_structure_panel(record: PlacementRecord) -> bool:
    return record.system == "structure" and any("panel" in part for part in record.path)


def build_figure(
    placements: list[PlacementRecord],
    envelope: Vec3,
    *,
    systems: set[str] | None = None,
    show_envelope: bool = True,
    translucent_large: bool = True,
) -> go.Figure:
    """Build an interactive Plotly figure for placement boxes."""

    filtered = [record for record in placements if systems is None or record.system in systems]
    fig = go.Figure()
    if show_envelope:
        fig.add_trace(envelope_trace(envelope))

    legend_seen: set[str] = set()
    for record in filtered:
        fig.add_trace(box_trace(record, envelope, legend_seen, translucent_large))
        legend_seen.add(record.system)

    for trace in axis_traces(envelope):
        fig.add_trace(trace)

    fig.update_layout(
        height=760,
        margin={"l": 0, "r": 0, "t": 28, "b": 0},
        template="plotly_white",
        uirevision="satellite-box-viewer",
        legend={"title": {"text": "system"}, "itemsizing": "constant"},
        scene={
            "aspectmode": "data",
            "camera": {
                "eye": {"x": 1.25, "y": -1.6, "z": 1.1},
                "up": {"x": 0, "y": 0, "z": 1},
            },
            "xaxis": axis_layout("X [mm]"),
            "yaxis": axis_layout("Y [mm]"),
            "zaxis": axis_layout("Z [mm]"),
        },
    )
    return fig


def box_trace(
    record: PlacementRecord,
    envelope: Vec3,
    legend_seen: set[str],
    translucent_large: bool,
) -> go.Mesh3d:
    vertices = box_vertices(record, envelope)
    x, y, z = zip(*vertices, strict=True)
    color = SYSTEM_PALETTE.get(record.system, "#8f8f8f")
    hover = hover_text(record)
    return go.Mesh3d(
        x=x,
        y=y,
        z=z,
        i=MESH_I,
        j=MESH_J,
        k=MESH_K,
        color=color,
        opacity=box_opacity(record, envelope, translucent_large),
        flatshading=True,
        name=record.system,
        legendgroup=record.system,
        showlegend=record.system not in legend_seen,
        hovertext=[hover] * len(vertices),
        hoverinfo="text",
        lighting={"ambient": 0.58, "diffuse": 0.78, "specular": 0.12, "roughness": 0.82},
    )


def box_vertices(record: PlacementRecord, envelope: Vec3) -> tuple[Vec3, ...]:
    center = box_center(record, envelope)
    half = tuple(size / 2.0 for size in record.size)
    offsets = (
        (-half[0], -half[1], -half[2]),
        (half[0], -half[1], -half[2]),
        (half[0], half[1], -half[2]),
        (-half[0], half[1], -half[2]),
        (-half[0], -half[1], half[2]),
        (half[0], -half[1], half[2]),
        (half[0], half[1], half[2]),
        (-half[0], half[1], half[2]),
    )
    return tuple(add_vec3(center, rotate_offset(offset, record)) for offset in offsets)


def rotate_offset(offset: Vec3, record: PlacementRecord) -> Vec3:
    normal = FACE_NORMALS[record.face]
    if normal is None or record.rz == 0.0:
        return offset

    axis_index, sign = normal
    radians = math.radians(record.rz * sign)
    sin_value = math.sin(radians)
    cos_value = math.cos(radians)
    rotated = list(offset)
    axes = [index for index in range(3) if index != axis_index]
    first, second = axes
    rotated[first] = offset[first] * cos_value - offset[second] * sin_value
    rotated[second] = offset[first] * sin_value + offset[second] * cos_value
    return (rotated[0], rotated[1], rotated[2])


def box_opacity(record: PlacementRecord, envelope: Vec3, translucent_large: bool) -> float:
    is_large = is_envelope_sized(record.size, envelope) or is_structure_frame(record)
    if translucent_large and is_large:
        return 0.2
    return 0.9


def is_structure_frame(record: PlacementRecord) -> bool:
    return record.system == "structure" and any(part == "frames" for part in record.path)


def hover_text(record: PlacementRecord) -> str:
    dx, dy, dz = (format_number(value) for value in record.size)
    return f"{record.system} / {record.name} / {record.face} / {dx}×{dy}×{dz} mm"


def envelope_trace(envelope: Vec3) -> go.Scatter3d:
    corners = box_corners(envelope)
    x: list[float | None] = []
    y: list[float | None] = []
    z: list[float | None] = []
    for start, end in ENVELOPE_EDGE_INDEXES:
        segment = (corners[start], corners[end])
        x.extend([segment[0][0], segment[1][0], None])
        y.extend([segment[0][1], segment[1][1], None])
        z.extend([segment[0][2], segment[1][2], None])

    return go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="lines",
        name="envelope",
        line={"color": "#2f3542", "width": 3},
        hoverinfo="skip",
        showlegend=False,
    )


def box_corners(size: Vec3) -> tuple[Vec3, ...]:
    half = tuple(value / 2.0 for value in size)
    return (
        (-half[0], -half[1], -half[2]),
        (half[0], -half[1], -half[2]),
        (half[0], half[1], -half[2]),
        (-half[0], half[1], -half[2]),
        (-half[0], -half[1], half[2]),
        (half[0], -half[1], half[2]),
        (half[0], half[1], half[2]),
        (-half[0], half[1], half[2]),
    )


def axis_traces(envelope: Vec3) -> tuple[go.Scatter3d, go.Scatter3d, go.Scatter3d]:
    length = max(max(envelope) * 0.38, 1.0)
    return (
        axis_trace("X", "#d62728", (length, 0.0, 0.0)),
        axis_trace("Y", "#2ca02c", (0.0, length, 0.0)),
        axis_trace("Z", "#1f77b4", (0.0, 0.0, length)),
    )


def axis_trace(label: str, color: str, end: Vec3) -> go.Scatter3d:
    return go.Scatter3d(
        x=[0.0, end[0]],
        y=[0.0, end[1]],
        z=[0.0, end[2]],
        mode="lines+text",
        text=["", label],
        textposition="top center",
        textfont={"color": color, "size": 14},
        line={"color": color, "width": 5},
        hoverinfo="skip",
        showlegend=False,
    )


def axis_layout(title: str) -> dict[str, Any]:
    return {
        "title": {"text": title},
        "showbackground": False,
        "zeroline": True,
        "showspikes": False,
    }


def add_vec3(left: Vec3, right: Vec3) -> Vec3:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")
