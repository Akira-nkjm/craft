"""Thermal system analyses。

ONGLAISAT 熱制御解析。**多ノード過渡ソルバ（toolbox.thermal）** を craft データ
から駆動し、一軌道（1 周期）分のノード温度履歴を求める。各 PowerConsuming コンポ
を個別の内部ノード（InternalPanelNode）として扱い、その発熱はモード別 power_modes
から算出する（手書き定数を使わない）。機体は 6 面 box として外面ノードに展開する。

ノード化方針（方針 B）:
    - 各 Placeable コンポを個別 InternalPanelNode に。
    - internal_heat_w = 当該モード発熱 = power_per_unit_w × quantity（ON のときのみ）。
    - heat_capacity_j_k = mass × quantity × node_specific_heat_j_kg_k（下限 1.0）。
    - conductances_w_k = ((搭載面, node_conductance_w_k),)。搭載面は placement.face を
      6 面 box にマップ。

入力は全て data 参照（panel_surfaces / thermalmodel / orbital）と全コンポ収集
（vq.Collect(tag="Component")）で受け取り、Python 側に物理値をハードコードしない。

残置している旧・単純解析（orbit_solar_heat_on_sap_w / radiator_equilibrium_temp_c /
heater_max_power_w）は β=0 定常近似のクイックチェック用。

参照データ:
    - 軌道: 高度 410 km（ISS 放出）、β=0（最悪低温・最大食）[orbital / thermalmodel]
    - 機体外面 α: 0.20 (PX/MX/PY/MY), 0.30 (PZ/MZ) [panel_surfaces / S2E-AOBC]
    - 内面: 黒塗装既定（α=0.9, ε=0.85）
    - BAT_HTR: 2.88W、全モード待機 ON（サーモスタット制御）[heaters / BatteryMD §5]
"""

import math
from typing import Annotated, Any

import veriq as vq
from toolbox.thermal import (
    AnalysisSettings,
    Material,
    OpticalFinish,
    OpticalMaterial,
    PanelLayer,
    SpacecraftThermalConfig,
    SurfaceNode,
    ThermalEnvironment,
    run_earth_orbit_analysis,
)
from toolbox.thermal.nodes import InternalPanelNode
from toolbox.thermal.orbit_heat import orbit_parameters

from craft.analyses import face_of, heat_for_mode, iter_instances, mass_quantity_kg
from craft.schema import analysis

# ──────────────────────────────────────────────────────────────────────────────
# 定数・面マップ
# ──────────────────────────────────────────────────────────────────────────────

_SOLAR_CONSTANT_W_M2 = 1367.0  # 太陽定数 [W/m²]（物理定数。旧・単純解析用）
_SIGMA_W_M2_K4 = 5.67e-8  # ステファン・ボルツマン定数（物理定数。旧・単純解析用）

# placement.face（円筒系含む）→ 機体 6 面 box へのマップ。
# PX/MX/PY/MY/PZ/MZ はそのまま。None / 不明は "PZ"（天頂面）へフォールバック。
_FACE_MAP: dict[str, str] = {
    "PX": "PX",
    "MX": "MX",
    "PY": "PY",
    "MY": "MY",
    "PZ": "PZ",
    "MZ": "MZ",
    "C": "PZ",
    "CY+": "PY",
    "CY-": "MY",
    "CX+": "PX",
    "CX-": "MX",
    "CZ+": "PZ",
    "CZ-": "MZ",
}
_DEFAULT_FACE = "PZ"

# 内面（機体内側）の既定光学物性（黒塗装）。
_INSIDE_ALPHA = 0.9
_INSIDE_EPSILON = 0.85


def _mapped_face(inst: Any) -> str:
    """コンポの placement.face を機体 6 面 box にマップ（不明は天頂 PZ）。"""
    face = face_of(inst)
    if face is None:
        return _DEFAULT_FACE
    return _FACE_MAP.get(face, _DEFAULT_FACE)


def _is_thermal_node(inst: Any) -> bool:
    """質量または発熱（いずれかのモードで）を持つ = 熱ノード化対象か。

    純パッシブ（質量 0 かつ全モード発熱 0）はノード化しない。
    """
    if mass_quantity_kg(inst) > 0.0:
        return True
    power_modes = getattr(getattr(inst, "design", None), "power_modes", None)
    if not power_modes:
        return False
    power = getattr(getattr(inst, "spec", None), "power_per_unit_w", 0.0) or 0.0
    return power > 0.0 and any(power_modes.values())


def _iter_thermal_nodes(loads: dict) -> list[tuple[str, Any]]:
    """ノード化対象コンポを (一意名, inst) の決定的リストで返す。

    名前は `<型名>_<連番>`。同一 loads に対して常に同じ順序・同じ名前を返すので、
    config 組み立てと verify 側のノード名引き当てが一致する。
    """
    nodes: list[tuple[str, Any]] = []
    counters: dict[str, int] = {}
    for tbl in loads.values():
        for inst in iter_instances(tbl):
            if not _is_thermal_node(inst):
                continue
            type_name = type(inst).__name__
            idx = counters.get(type_name, 0)
            counters[type_name] = idx + 1
            nodes.append((f"{type_name}_{idx}", inst))
    return nodes


def _all_modes(loads: dict) -> list[str]:
    """収集した全コンポの power_modes キーの和集合（解析対象モード一覧）。"""
    modes: set[str] = set()
    for tbl in loads.values():
        for inst in iter_instances(tbl):
            power_modes = getattr(getattr(inst, "design", None), "power_modes", None)
            if power_modes:
                modes.update(power_modes.keys())
    return sorted(modes)


# ──────────────────────────────────────────────────────────────────────────────
# 多ノード過渡解析の組み立て・実行
# ──────────────────────────────────────────────────────────────────────────────


def _build_surfaces(thermalmodel: Any, panel_surfaces: Any) -> tuple[SurfaceNode, ...]:
    """機体 6 面の外面ノードを構築する（α/ε は panel_surfaces 参照）。"""
    lx = thermalmodel.body_size_x_m
    ly = thermalmodel.body_size_y_m
    lz = thermalmodel.body_size_z_m
    material = Material(
        name="BodyPanel",
        density_kg_m3=thermalmodel.panel_density_kg_m3,
        specific_heat_j_kg_k=thermalmodel.panel_specific_heat_j_kg_k,
    )
    panel = PanelLayer(material=material, thickness_m=thermalmodel.panel_thickness_m)
    inside = (OpticalFinish(OpticalMaterial("Inside", _INSIDE_ALPHA, _INSIDE_EPSILON), 1.0),)

    def _optical(surface_key: str) -> tuple[OpticalFinish, ...]:
        surf = panel_surfaces[surface_key].spec
        mat = OpticalMaterial(surface_key, alpha=surf.absorptivity, epsilon=surf.emissivity)
        return (OpticalFinish(mat, 1.0),)

    # face → (normal, area, panel_surfaces キー)
    # PZ は太陽指向面（sun_pointing 姿勢で +Z=太陽方向）。実機では展開 SAP が
    # この面を覆うため、外面光学を発電面 sap_front（α=0.90, ε=0.85）で近似する。
    # NOTE: 近似。展開 SAP を機体 +Z 面と一体扱いするため、SAP ウィング単体の
    # 温度（機体から熱的に浮いた高温/低温振幅）は分離できない。SAP 単体温度が
    # 要る場合は独立放熱ノード化（toolbox 拡張）が必要。
    defs = (
        ("PX", (1.0, 0.0, 0.0), ly * lz, "body_px_mx"),
        ("MX", (-1.0, 0.0, 0.0), ly * lz, "body_px_mx"),
        ("PY", (0.0, 1.0, 0.0), lx * lz, "body_py_my"),
        ("MY", (0.0, -1.0, 0.0), lx * lz, "body_py_my"),
        ("PZ", (0.0, 0.0, 1.0), lx * ly, "sap_front"),
        ("MZ", (0.0, 0.0, -1.0), lx * ly, "body_pz_mz"),
    )
    return tuple(
        SurfaceNode(
            name=name,
            normal=normal,
            area_m2=area,
            panel=panel,
            outside=_optical(key),
            inside=inside,
        )
        for name, normal, area, key in defs
    )


def _build_component_nodes(
    loads: dict, thermalmodel: Any, mode: str
) -> tuple[InternalPanelNode, ...]:
    """各コンポノードを個別 InternalPanelNode に変換する（方針 B）。"""
    cp = thermalmodel.node_specific_heat_j_kg_k
    g = thermalmodel.node_conductance_w_k
    nodes: list[InternalPanelNode] = []
    for node_name, inst in _iter_thermal_nodes(loads):
        mass = mass_quantity_kg(inst)
        heat = heat_for_mode(inst, mode)
        heat_capacity = max(mass * cp, 1.0)  # mass=0 のヒータ等の 0 を防ぐ下限ガード
        nodes.append(
            InternalPanelNode(
                name=node_name,
                heat_capacity_j_k=heat_capacity,
                conductances_w_k=((_mapped_face(inst), g),),
                internal_heat_w=heat,
            )
        )
    return tuple(nodes)


def _build_config(
    loads: dict, thermalmodel: Any, panel_surfaces: Any, mode: str
) -> SpacecraftThermalConfig:
    """指定モードの SpacecraftThermalConfig を組み立てる。"""
    surfaces = _build_surfaces(thermalmodel, panel_surfaces)
    panels = _build_component_nodes(loads, thermalmodel, mode)
    initial_k = thermalmodel.initial_temperature_c + 273.15
    return SpacecraftThermalConfig(
        surfaces=surfaces,
        dimensions_m=(
            thermalmodel.body_size_x_m,
            thermalmodel.body_size_y_m,
            thermalmodel.body_size_z_m,
        ),
        internal_panels=panels,
        environment=ThermalEnvironment(),
        analysis=AnalysisSettings(
            initial_temperature_k=initial_k,
            time_step_s=thermalmodel.time_step_s,
        ),
    )


def _run_all_modes(
    loads: dict, thermalmodel: Any, panel_surfaces: Any, altitude_km: float
) -> dict[str, tuple[float, float]]:
    """全モード横断で各ノードの (min_c, max_c) [degC] を集約する。

    モード一覧は収集コンポの power_modes キー和集合。各モードで
    ``settle_orbits`` 周回して周期定常（periodic steady state）に近づけ、
    **最終 1 周だけ**を評価対象とする（初期温度 20℃ からのコールドスタート
    過渡を除去するため）。全モード横断の最小・最大温度を集める。純粋関数
    （入力は読み取り専用）。重複実行の抑止は呼び出し側の `thermal_node_temps`
    （veriq transient calc）が担い、下流の scalar / verify が
    `vq.Ref("@thermal_node_temps")` で結果を共有する。
    """
    beta = thermalmodel.beta_angle_deg
    n_orbits = max(1, int(thermalmodel.settle_orbits))
    period_s = orbit_parameters(altitude_km, beta)[0]
    duration_s = n_orbits * period_s
    last_orbit_start_s = (n_orbits - 1) * period_s

    modes = _all_modes(loads) or ["__static__"]
    agg: dict[str, tuple[float, float]] = {}
    for mode in modes:
        config = _build_config(loads, thermalmodel, panel_surfaces, mode)
        result = run_earth_orbit_analysis(
            config=config, altitude_km=altitude_km, beta_angle_deg=beta, duration_s=duration_s
        )
        # 最終 1 周のみで min/max を取る（周期定常近似）。
        last_orbit = result.times_s >= last_orbit_start_s
        for name, series in result.temperatures_k.items():
            window = series[last_orbit]
            lo_c = float(window.min()) - 273.15
            hi_c = float(window.max()) - 273.15
            if name in agg:
                prev_lo, prev_hi = agg[name]
                agg[name] = (min(prev_lo, lo_c), max(prev_hi, hi_c))
            else:
                agg[name] = (lo_c, hi_c)

    return agg


def _battery_range(node_temps: dict[str, tuple[float, float]]) -> tuple[float, float] | None:
    """ノード名に "batter" を含むノードの (min, max) を統合して返す（無ければ None）。"""
    los: list[float] = []
    his: list[float] = []
    for name, (lo, hi) in node_temps.items():
        if "batter" in name.lower():
            los.append(lo)
            his.append(hi)
    if not los:
        return None
    return (min(los), max(his))


def _component_node_ranges(
    node_temps: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    """外面（6 面 box）と MLI を除いたコンポノードのみを抽出する。"""
    surface_names = {"PX", "MX", "PY", "MY", "PZ", "MZ"}
    return {
        name: rng
        for name, rng in node_temps.items()
        if name not in surface_names and not name.endswith("_MLI")
    }


# ──────────────────────────────────────────────────────────────────────────────
# 公開 @analysis（多ノード過渡解析）
# ──────────────────────────────────────────────────────────────────────────────


@analysis(
    transient=True,
    desc="多ノード過渡解析の全モード横断ノード温度域 [degC]（Python オブジェクト, TOML 非出力）",
    imports=["thermal", "orbital"],
)
def thermal_node_temps(
    loads: Annotated[dict, vq.Collect(tag="Component")],
    thermalmodel: Annotated[Any, vq.Ref("$.thermalmodel")],
    panel_surfaces: Annotated[vq.Table, vq.Ref("$.panel_surfaces")],
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
) -> dict[str, tuple[float, float]]:
    """多ノード過渡ソルバを全モードで 1 回だけ走らせ、ノード温度域を返す。

    戻り値は {ノード名: (min_c, max_c)} の dict（外面・MLI・各コンポノードを含む）。
    transient=True なので結果は下流計算に Python オブジェクトとして渡されるが、
    merged.toml には出力されない。scalar / verify はこれを `vq.Ref("@thermal_node_temps")`
    で参照し、多ノード過渡解析が評価グラフ上で 1 回だけ評価されることを保証する。
    """
    return _run_all_modes(loads, thermalmodel, panel_surfaces, altitude_km)


@analysis(
    desc="バッテリノードの一軌道最低温度 [degC]（多ノード過渡, 全モード横断）",
    imports=["thermal"],
)
def battery_min_temp_c(
    node_temps: Annotated[dict, vq.Ref("@thermal_node_temps")],
    thermalmodel: Annotated[Any, vq.Ref("$.thermalmodel")],
) -> float:
    """バッテリ搭載ノードの一軌道最低温度 [degC]（全モード横断 min）。

    ノード名に "batter" を含むノードの統合 min を返す。バッテリノードが無い場合は
    初期温度にフォールバックする。
    """
    rng = _battery_range(node_temps)
    if rng is None:
        return thermalmodel.initial_temperature_c
    return rng[0]


@analysis(
    desc="バッテリノードの一軌道最高温度 [degC]（多ノード過渡, 全モード横断）",
    imports=["thermal"],
)
def battery_max_temp_c(
    node_temps: Annotated[dict, vq.Ref("@thermal_node_temps")],
    thermalmodel: Annotated[Any, vq.Ref("$.thermalmodel")],
) -> float:
    """バッテリ搭載ノードの一軌道最高温度 [degC]（全モード横断 max）。"""
    rng = _battery_range(node_temps)
    if rng is None:
        return thermalmodel.initial_temperature_c
    return rng[1]


@analysis(
    desc="全コンポノードの一軌道最高温度 [degC]（多ノード過渡, 全モード横断）",
    imports=["thermal"],
)
def max_component_temp_c(
    node_temps: Annotated[dict, vq.Ref("@thermal_node_temps")],
    thermalmodel: Annotated[Any, vq.Ref("$.thermalmodel")],
) -> float:
    """全コンポノード横断の一軌道最高温度 [degC]（外面・MLI を除く）。"""
    comp = _component_node_ranges(node_temps)
    if not comp:
        return thermalmodel.initial_temperature_c
    return max(hi for _, hi in comp.values())


@analysis(
    desc="全コンポノードの一軌道最低温度 [degC]（多ノード過渡, 全モード横断）",
    imports=["thermal"],
)
def min_component_temp_c(
    node_temps: Annotated[dict, vq.Ref("@thermal_node_temps")],
    thermalmodel: Annotated[Any, vq.Ref("$.thermalmodel")],
) -> float:
    """全コンポノード横断の一軌道最低温度 [degC]（外面・MLI を除く）。"""
    comp = _component_node_ranges(node_temps)
    if not comp:
        return thermalmodel.initial_temperature_c
    return min(lo for lo, _ in comp.values())


@analysis(
    verify=True,
    desc="各 TemperatureSensitive コンポの一軌道温度が動作温度範囲内に収まるか",
    imports=["thermal"],
)
def verify_components_within_temp_limits(
    node_temps: Annotated[dict, vq.Ref("@thermal_node_temps")],
    loads: Annotated[dict, vq.Collect(tag="Component")],
) -> bool:
    """temp_min_c / temp_max_c を持つコンポの一軌道 min/max が範囲内か検証する。

    対応するコンポノードが無いもの（質量・発熱ともゼロでノード化されない等）は
    スキップする。一つでも範囲外があれば False。
    """
    for node_name, inst in _iter_thermal_nodes(loads):
        spec = getattr(inst, "spec", None)
        tmin = getattr(spec, "temp_min_c", None)
        tmax = getattr(spec, "temp_max_c", None)
        if tmin is None or tmax is None:
            continue
        rng = node_temps.get(node_name)
        if rng is None:
            continue
        node_lo, node_hi = rng
        if bool(node_lo < tmin or node_hi > tmax):
            return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# 旧・単純解析（β=0 定常近似のクイックチェック。残置）
# ──────────────────────────────────────────────────────────────────────────────


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
    """SAP 発電面（PZ 向き）への軌道平均太陽熱入力 [W] を推算する（簡易チェック）。

    β=0 最悪条件、面法線 = +Z の単純化近似。日照平均 cos θ ≈ 1/π。
    多ノード過渡解析の前段クイックチェックとして残置。
    """
    absorptivity = panel_surfaces["sap_front"].spec.absorptivity
    cos_avg = 1.0 / math.pi  # β=0 円形軌道の日照平均 cos θ
    period_s = period_min * 60.0
    sunlit_fraction = 1.0 - (eclipse_s / period_s) if period_s > 0.0 else 0.0
    return _SOLAR_CONSTANT_W_M2 * area_m2 * absorptivity * cos_avg * sunlit_fraction


@analysis(
    desc="機体放熱面（PX/MX）の放射平衡温度 [degC]（ε/A=data 参照, Stefan-Boltzmann）",
    imports=["thermal"],
)
def radiator_equilibrium_temp_c(
    panel_surfaces: Annotated[vq.Table, vq.Ref("$.panel_surfaces")],
    internal_dissipation_w: Annotated[float, vq.Ref("$.thermalmodel.internal_dissipation_w")],
    radiator_area_m2: Annotated[float, vq.Ref("$.thermalmodel.radiator_area_m2")],
) -> float:
    """機体外面（PX/MX）の放射平衡温度 [degC]（蝕中・最悪低温 = 太陽入力 0）。

    内部発熱 = 放射排熱 を Stefan-Boltzmann 則で解く: T = (Q / (σ ε A))^(1/4)。
    多ノード過渡解析の前段クイックチェックとして残置。
    """
    emissivity = panel_surfaces["body_px_mx"].spec.emissivity
    q_in = internal_dissipation_w
    if q_in <= 0.0 or radiator_area_m2 <= 0.0 or emissivity <= 0.0:
        return -273.15
    t_k = (q_in / (_SIGMA_W_M2_K4 * emissivity * radiator_area_m2)) ** 0.25
    return t_k - 273.15


@analysis(desc="バッテリヒーター（BAT_HTR）最大消費電力 [W]")
def heater_max_power_w(
    heaters: Annotated[vq.Table, vq.Ref("$.heaters")],
) -> float:
    """全ヒーターの最大消費電力 [W]（全モード ON 時の最悪消費）。

    BAT_HTR: 2.88W（PCDU ch11, 12V/0.4A）[確定値: BatteryMD §5]
    """
    if not heaters:
        return 0.0
    return sum(
        h.spec.power_per_unit_w * h.design.quantity
        for h in heaters.values()
        if any(h.design.power_modes.values())
    )


@analysis(
    verify=True,
    desc="BAT_HTR の定格電力が目標温度制御に必要な最小電力（0W超）を満たすか",
)
def verify_heater_power_positive(
    max_power_w: Annotated[float, vq.Ref("@heater_max_power_w")],
) -> bool:
    """ヒーター最大消費電力 > 0W（搭載・電力供給有り）を確認する。

    BAT_HTR は eclipse 中バッテリを 10degC 以上に保持するために必要。
    """
    return max_power_w > 0.0
