"""Power system components.

注意: `from __future__ import annotations` は書かない（veriq の inspect.signature を壊す）。
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    PowerConsuming,
    TemperatureSensitive,
    fld,
)


class Battery(Component, MultiInstance, TemperatureSensitive, Placeable):
    """二次電池。eclipse 中の電力供給を担う。"""

    capacity_wh: float = fld(ge=0, unit="Wh", desc="Battery capacity")
    nominal_voltage_v: float = fld(ge=0, unit="V", default=0.0)
    manufacturer: str = fld(default="", desc="Manufacturer")

    class Design:
        depth_of_discharge: float = fld(ge=0, le=1, desc="設計時 DoD")

    class Requirements:
        depth_of_discharge_max: float = fld(default=0.8, gt=0, le=1, desc="要求 DoD 上限")


class SolarPanel(Component, MultiInstance, TemperatureSensitive, Placeable):
    """太陽電池パドル。"""

    area_m2: float = fld(ge=0, unit="m^2", desc="Panel area")
    default_power_generation_per_unit_w: float = fld(
        ge=0,
        unit="W",
        desc="想定発電量",
    )
    efficiency: float = fld(ge=0, le=1, default=0.28, desc="セル効率")

    class Design:
        cell_count: int = fld(ge=1)
        string_count: int = fld(ge=1)


class PDM(Component, MultiInstance, PowerConsuming, Placeable):
    """Power Distribution Module。"""

    rated_current_a: float = fld(ge=0, unit="A")

    class Design:
        efficiency: float = fld(ge=0, le=1, default=0.95)
