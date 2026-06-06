"""Orbital system analyses。

軌道高度から周期・速度・食割合を toolbox.orbital で算出し、data.toml の
格納値（period_min / eclipse_duration_s）と整合するかを検証する。

veriq 制約: scope に貼る引数は `Annotated[..., vq.Ref("$...")]`。
"""

from typing import Annotated

import veriq as vq
from toolbox.orbital.eclipse import eclipse_duration_s as tb_eclipse_duration_s
from toolbox.orbital.mechanics import (
    orbital_period_s as tb_orbital_period_s,
)
from toolbox.orbital.mechanics import (
    orbital_velocity_km_s as tb_orbital_velocity_km_s,
)

from craft.schema import analysis


@analysis(desc="軌道周期 [min]（toolbox.orbital_period_s, 円軌道）")
def orbital_period_min(
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km")],
) -> float:
    """高度から円軌道周期を算出 [min]。"""
    return tb_orbital_period_s(altitude_km=altitude_km) / 60.0


@analysis(desc="軌道速度 [km/s]（toolbox.orbital_velocity_km_s）")
def orbital_velocity_km_s(
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km")],
) -> float:
    """高度から円軌道速度を算出 [km/s]。"""
    return tb_orbital_velocity_km_s(altitude_km=altitude_km)


@analysis(desc="食割合 [%]（β=0 最悪、toolbox.eclipse_duration_s / 周期）")
def eclipse_fraction_pct(
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km")],
) -> float:
    """β=0 での 1 周期あたり食割合 [%]。"""
    period_s = tb_orbital_period_s(altitude_km=altitude_km)
    if period_s <= 0.0:
        return 0.0
    return tb_eclipse_duration_s(altitude_km=altitude_km, beta_angle_deg=0.0) / period_s * 100.0


@analysis(
    verify=True,
    desc="格納 eclipse_duration_s が toolbox 算出値と 5% 以内で整合するか",
)
def verify_eclipse_consistency(
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km")],
    stored_eclipse_s: Annotated[float, vq.Ref("$.orbitalparams.eclipse_duration_s")],
) -> bool:
    """data.toml の食時間が toolbox（β=0）算出値と整合するか（相対誤差 5% 以内）。"""
    computed = float(tb_eclipse_duration_s(altitude_km=altitude_km, beta_angle_deg=0.0))
    if computed <= 0.0:
        return False
    return abs(stored_eclipse_s - computed) / computed <= 0.05
