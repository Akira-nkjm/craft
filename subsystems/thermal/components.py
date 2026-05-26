"""Thermal subsystem components — SpecOnly trait の例を含む。"""

from schema import (
    Component,
    MultiInstance,
    PowerConsuming,
    SpecOnly,
    fld,
)


class Heater(Component, MultiInstance, PowerConsuming):
    """搭載ヒータ。PowerConsuming → 自動で power_modes 付き。"""

    rated_power_w: float = fld(ge=0, unit="W", desc="定格電力")
    target_temperature_c: float = fld(unit="degC", desc="目標温度")

    class Design:
        hysteresis_c: float = fld(ge=0, default=2.0, unit="degC", desc="ヒステリシス幅")


class PanelSurface(Component, MultiInstance, SpecOnly):
    """パネル表面の熱光学物性。material library として複数種、Design なし。"""

    emissivity: float = fld(ge=0, le=1, desc="放射率")
    absorptivity: float = fld(ge=0, le=1, desc="太陽光吸収率")
    surface_treatment: str = fld(default="", desc="表面処理（白塗装/MLI 等）")
