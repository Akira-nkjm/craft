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
    """二次電池。eclipse 中の電力供給を担う。

    ONGLAISAT: Li-ion 2P3S パック（SPHERE-1 EYE 共通 6U バス、同型モジュール）。
    """

    capacity_wh: float = fld(ge=0, unit="Wh", desc="パックエネルギー")
    capacity_ah: float = fld(ge=0, unit="Ah", default=0.0, desc="パック容量（並列込み）")
    nominal_voltage_v: float = fld(ge=0, unit="V", default=0.0, desc="パック公称電圧")
    series_count: int = fld(ge=1, default=1, desc="直列セル数")
    parallel_count: int = fld(ge=1, default=1, desc="並列セル数")
    max_charge_voltage_v: float = fld(ge=0, unit="V", default=0.0, desc="CV 充電電圧上限")
    charge_current_rate_c: float = fld(ge=0, unit="1/h", default=0.0, desc="CC 充電レート [C]")
    internal_resistance_ohm: float = fld(ge=0, unit="ohm", default=0.0, desc="内部+配線抵抗")
    manufacturer: str = fld(default="", desc="Manufacturer")

    class Design:
        depth_of_discharge: float = fld(ge=0, le=1, desc="設計時 DoD（初期）")

    class Requirements:
        depth_of_discharge_max: float = fld(default=0.8, gt=0, le=1, desc="要求 DoD 上限")


class SolarPanel(Component, MultiInstance, TemperatureSensitive, Placeable):
    """太陽電池パドル（アレイ）。

    ONGLAISAT: CESI CTJ30 三接合セル、7 直 × 8 並 = 56 セルアレイ（MPPT 制御）。
    `default_power_generation_per_unit_w` はインスタンス（アレイ）あたりの発生電力。
    """

    area_m2: float = fld(ge=0, unit="m^2", desc="アレイ総セル面積")
    default_power_generation_per_unit_w: float = fld(
        ge=0,
        unit="W",
        desc="BOL 発生電力（MPPT 損失込み）",
    )
    bol_power_w: float = fld(ge=0, unit="W", default=0.0, desc="BOL 発生電力（MPPT 込み）")
    eol_power_w: float = fld(ge=0, unit="W", default=0.0, desc="EOL 発生電力（MPPT 込み）")
    efficiency: float = fld(ge=0, le=1, default=0.28, desc="セル効率 @AM0")
    cell_type: str = fld(default="", desc="セル品種")

    class Design:
        cell_count: int = fld(ge=1)
        string_count: int = fld(ge=1)


class PDM(Component, MultiInstance, PowerConsuming, Placeable):
    """Power Control & Distribution Unit（電力制御・分配）。

    ONGLAISAT: PCDU_rev3、13 チャネル、12V/5V バス、MPPT・CC/CV 充放電制御。
    """

    rated_current_a: float = fld(ge=0, unit="A")
    bus_voltage_v: float = fld(ge=0, unit="V", default=0.0, desc="主バス電圧")
    channel_count: int = fld(ge=0, default=0, desc="出力チャネル数")

    class Design:
        efficiency: float = fld(ge=0, le=1, default=0.95)
