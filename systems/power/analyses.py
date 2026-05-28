"""Power system analyses。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。

横断集計は `craft.analyses` のヘルパ（`power_per_mode` 等）を body 内で呼ぶ。
"""

from typing import Annotated

import veriq as vq

from craft.analyses import auto_inject_refs, power_per_mode
from craft.schema import analysis


@analysis(desc="全 PDM の想定消費電力合計（W） — 最大消費モードを採用")
def total_pdm_power_w(
    pdms: Annotated[vq.Table, vq.Ref("$.pdms")],
) -> float:
    """全 PDM の消費電力を、ON となるモードのうち最大消費電力で評価する。

    SEIRIOS のように多モード（safe/sun_acquisition/.../fine_ff）を持つ場合、
    特定モード名（旧 'nominal'）依存ではなく、PDM ごとに「ON となる任意モード」
    で消費電力を計上する。複数モード対応を意識した実装。
    """
    if not pdms:
        return 0.0
    return sum(p.spec.power_per_unit_w for p in pdms.values() if any(p.design.power_modes.values()))


@analysis(
    desc="モード別 PDM 消費電力 [W]（全モード一覧）",
    imports=["mission"],
)
def pdm_power_per_mode_w(
    pdms: Annotated[vq.Table, vq.Ref("$.pdms")],
    mode_configs: Annotated[vq.Table, vq.Ref("$.operation_mode_configs", scope="mission")],
) -> dict[str, float]:
    """各運用モードにおける PDM 消費電力合計を返す。

    mode_configs に登録されたモードのみ計算し、
    power_modes に未記載のモードはその PDM を off 扱いとする。
    """
    result: dict[str, float] = {}
    for mode_name in mode_configs:
        result[mode_name] = sum(
            p.spec.power_per_unit_w
            for p in pdms.values()
            if p.design.power_modes.get(mode_name, False)
        )
    return result


@analysis(verify=True, desc="全バッテリーが要求 DoD 制約を満たすか")
def verify_battery_capacity(
    batteries: Annotated[vq.Table, vq.Ref("$.batteries")],
) -> bool:
    """全 battery が `capacity * DoD_max >= 50 Wh` を満たすか（仮の要求値）。"""
    required_energy_wh = 50.0
    if not batteries:
        return False
    return all(
        b.spec.capacity_wh * b.requirements.depth_of_discharge_max >= required_energy_wh
        for b in batteries.values()
    )


@analysis(
    desc="軌道 1 周あたりに必要なエネルギー量 [Wh]",
    imports=["orbital"],
)
def required_orbit_energy_wh(
    pdm_power: Annotated[float, vq.Ref("@total_pdm_power_w")],
    eclipse_s: Annotated[float, vq.Ref("$.orbitalparams.eclipse_duration_s", scope="orbital")],
) -> float:
    """eclipse 中の必要エネルギー（W * 時間）。"""
    return pdm_power * eclipse_s / 3600.0


@analysis(desc="モード別 全バス消費電力 [W] — 全 PowerConsuming コンポを集計")
@auto_inject_refs(
    trait="PowerConsuming",
    extra_refs=[("mission", "operation_mode_configs")],
)
def bus_power_per_mode_w(mode_configs, *tables) -> dict[str, float]:
    """各運用モードにおける全 PowerConsuming コンポの消費電力合計 [W]。"""
    return power_per_mode(mode_configs, *tables)


# ─── (ad-hoc 例) — veriq 非登録、API/CLI 専用 ─────────────────────────


@analysis(system=None, desc="バッテリ EOL 容量推定（ad-hoc）", cache=True)
def battery_eol_capacity(
    initial_capacity_wh: float,
    years: float = 5.0,
    cycles_per_day: float = 1.0,
) -> float:
    """初期容量と寿命・サイクル数から degradation を加味した EOL 容量を返す。"""
    cycles_total = years * 365.0 * cycles_per_day
    degradation = min(0.2, 0.0001 * cycles_total)
    return initial_capacity_wh * (1.0 - degradation)
