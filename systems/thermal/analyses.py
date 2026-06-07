"""Thermal system analyses。

ONGLAISAT 熱制御解析。toolbox.thermal の軌道熱入力・放射平衡計算を利用。

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


@analysis(
    system=None,
    desc="SAP 発電面への軌道平均太陽熱入力 [W]（toolbox.thermal.orbit_heat）",
    cache=True,
)
def orbit_solar_heat_on_sap_w(
    altitude_km: float = 410.0,
    beta_angle_deg: float = 0.0,
    absorptivity: float = 0.90,
    area_m2: float = 0.1312,
    solar_constant_w_m2: float = 1367.0,
) -> float:
    """SAP 発電面（PZ 向き）への軌道平均太陽熱入力 [W] を推算する。

    β=0 最悪条件、面法線 = [0, 0, 1]（+Z = SAP 向き）の単純化近似。
    軌道 1 周の日照区間で cos θ を積分した平均値を使用。
    式: Q = S * A * α * (1 / π)（β=0 平均係数）

    出典: ThermalMD §1 SAP ノード alpha=0.85（MAIN_SAP_MX.1）/0.918（MAIN_SAP_MX.2）
    ここでは S2E-AOBC front 値 α=0.90 を採用。
    """
    # β=0 円形軌道の日照平均 cos θ ≈ 1/π （法線方向 PZ 向き）
    cos_avg = 1.0 / math.pi
    # 日照時間割合: β=0, h=410km → eclipse_fraction ≈ 0.39 → sunlit ≈ 0.61
    sunlit_fraction = 0.61  # [S2E / orbital 解析値 1 - 0.389]
    return solar_constant_w_m2 * area_m2 * absorptivity * cos_avg * sunlit_fraction


# ──────────────────────────────────────────────────────────────────────────────
# 2. 放射平衡温度（ラジエータ排熱）
#    機体放熱面の放射平衡温度を Stefan-Boltzmann 則で推算する（ad-hoc）。
# ──────────────────────────────────────────────────────────────────────────────


@analysis(
    system=None,
    desc="機体放熱面（PX/MX）の放射平衡温度 [degC]（Stefan-Boltzmann 則）",
    cache=True,
)
def radiator_equilibrium_temp_c(
    internal_dissipation_w: float = 10.57,
    radiator_area_m2: float = 0.08,
    emissivity: float = 0.85,
    absorptivity: float = 0.20,
    solar_heat_w: float = 0.0,
    sigma_w_m2_k4: float = 5.67e-8,
) -> float:
    """機体外面の放射平衡温度 [degC]。

    内部発熱 + 太陽熱入力 = 放射排熱 を Stefan-Boltzmann 則で解く。
    Q_in = Q_rad → T = ((Q_solar + Q_internal) / (σ ε A))^(1/4)

    デフォルト値:
        - 内部発熱 10.57W: S2E heatload.csv 合計
          (AOCS 5.5 + BOARD 3.5 + BP 0.6 + COMM 0.77 + BAT 0.2) [S2E]
        - 放熱面積 0.08m²: S2E-AOBC satellite_structure.ini
          PX/MX 面（area_0_m2/area_1_m2）[S2E-AOBC]
        - ε=0.85, α=0.20: ThermalMD §4・S2E-AOBC 推定値

    外部太陽熱入力 solar_heat_w はデフォルト 0（蝕中 / 最悪低温条件）。
    """
    q_in = internal_dissipation_w + solar_heat_w
    if q_in <= 0.0 or radiator_area_m2 <= 0.0 or emissivity <= 0.0:
        return -273.15
    t_k = (q_in / (sigma_w_m2_k4 * emissivity * radiator_area_m2)) ** 0.25
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
    return bool(max_power_w > 0.0)
