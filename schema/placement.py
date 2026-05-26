"""Placement model — component placement parameters for CAD/mock layout."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class Placement(BaseModel):
    """Component placement parameters for CAD/mock layout generation."""

    face: Annotated[
        Literal["PX", "MX", "PY", "MY", "PZ", "MZ", "C", "CY+", "CY-", "CX+", "CX-", "CZ+", "CZ-"],
        Field(description="Panel face to mount on"),
    ]
    u: float = Field(default=0.0, ge=0.0, description="Position along face u-axis [mm]")
    v: float = Field(default=0.0, ge=0.0, description="Position along face v-axis [mm]")
    w: float = Field(default=0.0, ge=0.0, description="Offset from face surface [mm]")
    dx: float = Field(default=0.0, ge=0.0, description="Bounding box x dimension [mm]")
    dy: float = Field(default=0.0, ge=0.0, description="Bounding box y dimension [mm]")
    dz: float = Field(default=0.0, ge=0.0, description="Bounding box z dimension [mm]")
    rz: float = Field(default=0.0, description="Rotation around face normal [degrees]")
    side: Literal["IN", "OUT"] = Field(default="IN", description="Mount on inner or outer face")
    cad_file: str = Field(default="", description="CAD document name (empty = generate box)")
    cad_offset_x: float = Field(default=0.0, description="CAD bounding box center offset x [mm]")
    cad_offset_y: float = Field(default=0.0, description="CAD bounding box center offset y [mm]")
    cad_offset_z: float = Field(default=0.0, description="CAD bounding box center offset z [mm]")
    update_bbox: int = Field(
        default=0, ge=0, le=1, description="Set to 1 to auto-update bbox from CAD"
    )
