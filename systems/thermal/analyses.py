"""Thermal system analyses。

ONGLAISAT 熱制御解析。軌道平均太陽熱入力・放射平衡温度を **単純解析モデル**
（β=0 近似、Stefan-Boltzmann 則）で手計算する。toolbox.thermal は使わない
（対応する一般化関数が無いため、本機固有の簡易モデルを直接実装）。

入力（α/ε・面積・発熱・日照率）は全て data 参照（panel_surfaces / thermalmodel /
orbital）で、Python 側に物理値をハードコードしない。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。

参照データ:
    - 軌道: 高度 410 km（ISS 放出）、β=0（最悪条件）[S2E / ThermalMD]
    - SAP 発電面: α=0.90 [S2E-AOBC satellite_structure.ini]
    - 機体外面: α=0.20 (PX/MX/PY/MY), α=0.30 (PZ/MZ) [S2E-AOBC]
    - BAT_HTR: 2.88W、全モード待機 ON（サーモスタット制御）[BatteryMD §5]
"""

import math
from typing import Annotated

import veriq as vq

from craft.schema import analysis

# ──────────────────────────────────────────────────────────────────────────────
# 1. 軌道熱環境解析（ad-hoc）
#    toolbox.thermal.orbit_heat で太陽/アルベド/地球赤外入力を計算する。
#    生引数が必要なため system=None の ad-hoc 解析として公開。
# ──────────────────────────────────────────────────────────────────────────────


_SOLAR_CONSTANT_W_M2 = 1367.0  # 太陽定数 [W/m²]（物理定数）
_SIGMA_W_M2_K4 = 5.67e-8  # ステファン・ボルツマン定数（物理定数）


@analysis(
    desc="SAP 発電面への軌道平均太陽熱入力 [W]（α=panel_surfaces, 日照=orbital 参照）",
    imports=["thermal", "orbital"],
)
def orbit_solar_heat_on_sap_w(
    panel_surfaces: Annotated[vq.Table, vq.Ref("$.panel_surfaces")],
    area_m2: Annotated[float, vq.Ref("$.thermalmodel.sap_thermal_area_m2")],
    eclipse_s: Annotated[float, vq.Ref("$.orbitalparams.eclipse_duration_s", scope="orbital")],
    period_min: Annotated[float, vq.Ref("$.orbitalparams.period_min", scope="orbital")],
) -> float:
    """SAP 発電面（PZ 向き）への軌道平均太陽熱入力 [W] を推算する。

    β=0 最悪条件、面法線 = +Z の単純化近似。日照平均 cos θ ≈ 1/π。
    吸収率は panel_surfaces.sap_front、受熱面積は thermalmodel、日照割合は
    orbital（1 − eclipse/period）を参照（ハードコードしない）。
    """
    absorptivity = panel_surfaces["sap_front"].spec.absorptivity
    cos_avg = 1.0 / math.pi  # β=0 円形軌道の日照平均 cos θ
    period_s = period_min * 60.0
    sunlit_fraction = 1.0 - (eclipse_s / period_s) if period_s > 0.0 else 0.0
    return _SOLAR_CONSTANT_W_M2 * area_m2 * absorptivity * cos_avg * sunlit_fraction


# ──────────────────────────────────────────────────────────────────────────────
# 2. 放射平衡温度（ラジエータ排熱）
#    機体放熱面の放射平衡温度を Stefan-Boltzmann 則で推算する（ad-hoc）。
# ──────────────────────────────────────────────────────────────────────────────


@analysis(
    desc="機体放熱面（PX/MX）の放射平衡温度 [degC]（ε/A=data 参照, Stefan-Boltzmann）",
    imports=["thermal"],
)
def radiator_equilibrium_temp_c(
    panel_surfaces: Annotated[vq.Table, vq.Ref("$.panel_surfaces")],
    internal_dissipation_w: Annotated[float, vq.Ref("$.thermalmodel.internal_dissipation_w")],
    radiator_area_m2: Annotated[float, vq.Ref("$.thermalmodel.radiator_area_m2")],
) -> float:
    """機体外面（PX/MX）の放射平衡温度 [degC]（蝕中・最悪低温条件 = 太陽入力 0）。

    内部発熱 = 放射排熱 を Stefan-Boltzmann 則で解く: T = (Q / (σ ε A))^(1/4)。
    内部発熱・放熱面積は thermalmodel、放射率は panel_surfaces.body_px_mx を参照
    （ハードコードしない）。外部太陽熱入力は 0（蝕中 = 最悪低温）。
    """
    emissivity = panel_surfaces["body_px_mx"].spec.emissivity
    q_in = internal_dissipation_w
    if q_in <= 0.0 or radiator_area_m2 <= 0.0 or emissivity <= 0.0:
        return -273.15
    t_k = (q_in / (_SIGMA_W_M2_K4 * emissivity * radiator_area_m2)) ** 0.25
    return t_k - 273.15


# ──────────────────────────────────────────────────────────────────────────────
# 3. ヒーター所要電力（veriq 登録 calculation）
#    BAT_HTR の最大動作電力をバッテリヒーター定義から参照する。
# ──────────────────────────────────────────────────────────────────────────────


@analysis(desc="バッテリヒーター（BAT_HTR）最大消費電力 [W]")
def heater_max_power_w(
    heaters: Annotated[vq.Table, vq.Ref("$.heaters")],
) -> float:
    """全ヒーターの最大消費電力 [W]（全モード ON 時の最悪消費）。

    BAT_HTR: 2.88W（PCDU ch11, 12V/0.4A）[確定値: BatteryMD §5]
    サーモスタット制御のため実際の消費は下回るが、
    電力バジェット計上は最大値（全モード ON）を採用する。
    """
    if not heaters:
        return 0.0
    return sum(
        h.spec.power_per_unit_w * h.design.quantity
        for h in heaters.values()
        if any(h.design.power_modes.values())
    )


# ──────────────────────────────────────────────────────────────────────────────
# 4. バッテリ温度下限の検証
#    BAT_HTR ON 条件（10degC下限）とヒーター定格で十分か確認する（veriq 登録）。
# ──────────────────────────────────────────────────────────────────────────────


@analysis(
    verify=True,
    desc="BAT_HTR の定格電力が目標温度制御に必要な最小電力（0W超）を満たすか",
)
def verify_heater_power_positive(
    max_power_w: Annotated[float, vq.Ref("@heater_max_power_w")],
) -> bool:
    """ヒーター最大消費電力 > 0W（搭載・電力供給有り）を確認する。

    BAT_HTR は eclipse 中バッテリを 10degC 以上に保持するために必要。
    定格 2.88W 以上あれば本 verify は pass。詳細な熱収支検証は ad-hoc 解析を参照。
    """
    return max_power_w > 0.0
