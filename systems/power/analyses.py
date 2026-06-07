"""Power system analyses。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。

横断集計は `craft.analyses` のヘルパ（`power_per_mode` 等）を body 内で呼ぶ。
"""

from typing import Annotated

import veriq as vq
from toolbox.power.battery import (
    power_margin_pct as tb_power_margin_pct,
)
from toolbox.power.battery import (
    required_battery_capacity_wh as tb_required_battery_capacity_wh,
)
from toolbox.power.battery import (
    required_orbit_energy_wh as tb_required_orbit_energy_wh,
)
from toolbox.power.battery import (
    usable_capacity_wh as tb_usable_capacity_wh,
)

from craft.analyses import power_per_mode
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


@analysis(
    desc="モード別 全バス消費電力 [W] — 全 PowerConsuming コンポを集計",
    imports=["mission"],
)
def bus_power_per_mode_w(
    mode_configs: Annotated[
        vq.Table,
        vq.Ref("$.operation_mode_configs", scope="mission"),
    ],
    loads: Annotated[dict, vq.Collect(tag="PowerConsuming")],
) -> dict[str, float]:
    """各運用モードにおける全 PowerConsuming コンポの消費電力合計 [W]。"""
    return power_per_mode(mode_configs, *loads.values())


@analysis(desc="最悪ケース（全モード中最大）のバス消費電力 [W]")
def worst_case_bus_power_w(
    per_mode: Annotated[dict, vq.Ref("@bus_power_per_mode_w")],
) -> float:
    """全運用モードのうち最大のバス消費電力 [W]。電源サイジングの最悪条件。"""
    if not per_mode:
        return 0.0
    return max(per_mode.values())


@analysis(desc="日照中の発電電力（EOL）[W] — 全 SolarPanel の eol_power_w 合計")
def eol_generation_w(
    panels: Annotated[vq.Table, vq.Ref("$.solar_panels")],
) -> float:
    """EOL の発生電力合計 [W]（MPPT 損失込み）。"""
    if not panels:
        return 0.0
    return sum(p.spec.eol_power_w * p.design.quantity for p in panels.values())


@analysis(desc="実効バッテリエネルギー [Wh]（容量 × DoD_max, toolbox.usable_capacity_wh）")
def usable_battery_energy_wh(
    batteries: Annotated[vq.Table, vq.Ref("$.batteries")],
) -> float:
    """全バッテリの実効エネルギー合計 [Wh]。DoD 上限まで放電可能な分。"""
    if not batteries:
        return 0.0
    return sum(
        tb_usable_capacity_wh(b.spec.capacity_wh, b.requirements.depth_of_discharge_max)
        * b.design.quantity
        for b in batteries.values()
    )


@analysis(
    desc="軌道 1 周あたり蝕中に必要なエネルギー [Wh]（toolbox.required_orbit_energy_wh）",
    imports=["orbital"],
)
def required_orbit_energy_wh(
    load_w: Annotated[float, vq.Ref("@worst_case_bus_power_w")],
    eclipse_s: Annotated[float, vq.Ref("$.orbitalparams.eclipse_duration_s", scope="orbital")],
) -> float:
    """蝕中の最悪負荷を賄うのに必要な 1 軌道あたりエネルギー [Wh]。"""
    return tb_required_orbit_energy_wh(load_w, eclipse_s)


@analysis(desc="EOL 電力マージン [%]（発電EOL vs 最悪バス負荷, toolbox.power_margin_pct）")
def eol_power_margin_pct(
    gen_w: Annotated[float, vq.Ref("@eol_generation_w")],
    load_w: Annotated[float, vq.Ref("@worst_case_bus_power_w")],
) -> float:
    """日照時の EOL 電力マージン [%]。PDR 段階では >= 20% が目安。"""
    if gen_w <= 0.0:
        return 0.0
    return tb_power_margin_pct(gen_w, load_w)


@analysis(
    verify=True,
    desc="実効バッテリ容量が蝕中必要エネルギーを満たすか",
)
def verify_battery_capacity(
    usable_wh: Annotated[float, vq.Ref("@usable_battery_energy_wh")],
    required_wh: Annotated[float, vq.Ref("@required_orbit_energy_wh")],
) -> bool:
    """実効バッテリエネルギー >= 蝕中必要エネルギー（最悪負荷）を満たすか。"""
    return usable_wh > 0.0 and usable_wh >= required_wh


@analysis(desc="持続運用（精三軸指向）負荷に対する EOL 電力マージン [%]")
def sustained_power_margin_pct(
    per_mode: Annotated[dict, vq.Ref("@bus_power_per_mode_w")],
    gen_w: Annotated[float, vq.Ref("@eol_generation_w")],
) -> float:
    """精三軸指向（撮像待機）の持続負荷に対する EOL 発電マージン [%]。

    撮像・X帯DL のピーク負荷は短時間でバッテリ併用前提（@eol_power_margin_pct が
    薄いのはこのため）。持続的にバランスすべきは精三軸指向の負荷で、ここに十分な
    マージンがあることを別途評価する。
    """
    sustained_w = per_mode.get("fine_three_axis", 0.0)
    if gen_w <= 0.0:
        return 0.0
    return tb_power_margin_pct(gen_w, sustained_w)


@analysis(
    verify=True,
    desc="持続運用負荷に対し EOL 発電が >= 20% マージンを持つか（ピークはバッテリ併用）",
)
def verify_sustained_power_margin(
    margin_pct: Annotated[float, vq.Ref("@sustained_power_margin_pct")],
) -> bool:
    """持続運用（精三軸）の EOL 電力マージンが PDR 目安 >= 20% を満たすか。

    撮像/X帯DL の瞬時ピーク（@worst_case_bus_power_w 46.88W）は EOL 発電 50.53W に
    肉薄するが短時間イベントでバッテリが補填する設計（Power Overview §6）。
    持続成立条件は精三軸負荷に対するマージンで判定する。
    """
    return margin_pct >= 20.0


# ─── (ad-hoc 例) — veriq 非登録、API/CLI 専用 ─────────────────────────


@analysis(
    system=None,
    desc="必要バッテリ容量 [Wh]（toolbox.power.battery の式を利用）",
    cache=True,
)
def battery_capacity_required_wh(
    eclipse_load_w: float,
    eclipse_duration_h: float,
    dod_max: float,
    discharge_efficiency: float = 0.95,
) -> float:
    """toolbox の式をそのまま craft の analysis として公開する（パターン A: ラッパー）。

    物理式は toolbox 側（astropy で次元・参照値を検証済み）にあり、craft は
    引数を受けて呼ぶだけ。craft 内に式を直書きする従来パターンと併存できる。
    """
    return tb_required_battery_capacity_wh(
        eclipse_load_w, eclipse_duration_h, dod_max, discharge_efficiency
    )


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
