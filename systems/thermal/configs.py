"""Thermal system configurations。

熱解析のモデルパラメータ（機体寸法・パネル熱物性・ノード代表値）を data 駆動に
するための config。表面光学特性（α/ε）は PanelSurface、日照割合は orbital を
参照し、ここには熱モデル固有の幾何・熱物性（single source）を置く。

多ノード過渡解析（toolbox.thermal）はこの config と全 PowerConsuming コンポの
power_modes / mass から各ノードの内部発熱・熱容量・コンダクタンスを組み立てる。
"""

from craft.schema import Config, fld


class ThermalModel(Config):
    """熱解析モデルのパラメータ。

    Source: [S2E-AOBC] satellite_structure.ini（面積）、S2E heatload.csv（内部発熱）、
    structure frames bbox（機体寸法）。詳細 CAD / 熱解析で精緻化予定（[推定] 含む）。
    """

    # ─── 旧・単純解析（定常 Stefan-Boltzmann）用パラメータ（残置）─────────────
    sap_thermal_area_m2: float = fld(
        ge=0, default=0.1312, unit="m^2", desc="SAP 受熱面積（軌道熱入力評価用）[推定]"
    )
    radiator_area_m2: float = fld(
        ge=0, default=0.08, unit="m^2", desc="機体放熱面（PX/MX）面積 [S2E-AOBC]"
    )
    internal_dissipation_w: float = fld(
        ge=0,
        default=10.57,
        unit="W",
        desc="内部発熱合計（AOCS+BOARD+BP+COMM+BAT）[S2E heatload.csv]。"
        "新・多ノード過渡解析では power_modes から算出するため未参照（残置）",
    )

    # ─── 多ノード過渡解析（toolbox.thermal.run_earth_orbit_analysis）用 ────────
    body_size_x_m: float = fld(
        ge=0, default=0.1, unit="m", desc="機体 X 寸法 [structure frames bbox dx=100mm]"
    )
    body_size_y_m: float = fld(
        ge=0, default=0.2263, unit="m", desc="機体 Y 寸法 [structure frames bbox dy=226.3mm]"
    )
    body_size_z_m: float = fld(
        ge=0, default=0.366, unit="m", desc="機体 Z 寸法 [structure frames bbox dz=366mm]"
    )
    panel_thickness_m: float = fld(
        ge=0, default=0.002, unit="m", desc="外面パネル板厚 [推定: Al 2mm]"
    )
    panel_density_kg_m3: float = fld(
        ge=0, default=2700.0, unit="kg/m^3", desc="外面パネル材密度 [Al 6061]"
    )
    panel_specific_heat_j_kg_k: float = fld(
        ge=0, default=900.0, unit="J/(kg K)", desc="外面パネル材比熱 [Al 6061]"
    )
    node_specific_heat_j_kg_k: float = fld(
        ge=0,
        default=800.0,
        unit="J/(kg K)",
        desc="コンポ代表比熱（熱容量 = mass × cp の算出用）[推定: 電子機器 typical]",
    )
    node_conductance_w_k: float = fld(
        ge=0,
        default=0.5,
        unit="W/K",
        desc="コンポ⇔搭載面の代表熱コンダクタンス [推定: ボルト締結 typical]。"
        "explicit Euler の安定限界（dt < C_surface / Σg）も満たす値",
    )
    beta_angle_deg: float = fld(
        ge=0,
        default=0.0,
        unit="deg",
        desc="軌道面太陽角 β [deg]（0 = 最悪低温・最大食条件）",
    )
    time_step_s: float = fld(
        gt=0,
        default=5.0,
        unit="s",
        desc="過渡ソルバ時間刻み [s]（explicit Euler の安定限界を満たす）",
    )
    initial_temperature_c: float = fld(
        default=20.0, unit="degC", desc="ノード初期温度 [degC]（軌道投入前の機体温度）"
    )
