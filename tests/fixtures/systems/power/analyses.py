"""Power fixture analyses."""

from typing import Annotated

import veriq as vq

from craft.schema import analysis


@analysis(desc="全 PDM の想定消費電力合計（W）")
def total_pdm_power_w(pdms: Annotated[vq.Table, vq.Ref("$.pdms")]) -> float:
    if not pdms:
        return 0.0
    return sum(p.spec.power_per_unit_w for p in pdms.values() if any(p.design.power_modes.values()))


@analysis(desc="モード別 PDM 消費電力 [W]", imports=["mission"])
def pdm_power_per_mode_w(
    pdms: Annotated[vq.Table, vq.Ref("$.pdms")],
    mode_configs: Annotated[vq.Table, vq.Ref("$.operation_mode_configs", scope="mission")],
) -> dict[str, float]:
    return {
        mode_name: sum(
            p.spec.power_per_unit_w
            for p in pdms.values()
            if p.design.power_modes.get(mode_name, False)
        )
        for mode_name in mode_configs
    }


@analysis(verify=True, desc="全バッテリーが要求 DoD 制約を満たすか")
def verify_battery_capacity(batteries: Annotated[vq.Table, vq.Ref("$.batteries")]) -> bool:
    required_energy_wh = 50.0
    if not batteries:
        return False
    return all(
        b.spec.capacity_wh * b.requirements.depth_of_discharge_max >= required_energy_wh
        for b in batteries.values()
    )


@analysis(desc="軌道 1 周あたりに必要なエネルギー量 [Wh]", imports=["orbital"])
def required_orbit_energy_wh(
    pdm_power: Annotated[float, vq.Ref("@total_pdm_power_w")],
    eclipse_s: Annotated[float, vq.Ref("$.orbitalparams.eclipse_duration_s", scope="orbital")],
) -> float:
    return pdm_power * eclipse_s / 3600.0


@analysis(system=None, desc="バッテリ EOL 容量推定（ad-hoc）", cache=True)
def battery_eol_capacity(
    initial_capacity_wh: float,
    years: float = 5.0,
    cycles_per_day: float = 1.0,
) -> float:
    cycles_total = years * 365.0 * cycles_per_day
    degradation = min(0.2, 0.0001 * cycles_total)
    return initial_capacity_wh * (1.0 - degradation)
