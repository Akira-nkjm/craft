"""ONGLAISAT 多ノード過渡熱解析（toolbox.thermal 駆動）のテスト。

`tests/systems/` 配下なので conftest の isolation fixture は適用されず、実
`systems/` を読む。公開 @analysis は veriq 経由（run_analysis）で実データに対し、
private ヘルパは合成入力で単体検証する。
"""

from types import SimpleNamespace

import numpy as np
import pytest

from craft.core.analysis.runner import run_analysis

# NOTE: `systems.thermal.analyses` は **module top-level では import しない**。
# `tests/systems/conftest.py` の `real_systems_restored`（autouse）が各テスト前に
# 実 systems を reload して registry / scope を実データへ戻す。その後に lazy import
# することで、汚染後でも実データ用の解析・root model を確実に掴む。


@pytest.fixture
def ta(real_systems_restored):
    """実 systems reload 後に `systems.thermal.analyses` を lazy import して返す。

    多ノード過渡解析は veriq transient calc（`thermal_node_temps`）に集約され、
    手製メモ化（旧 `_RESULT_CACHE`）は廃止された。private ヘルパや veriq 経由
    @analysis を使うテストはこの fixture を引数で受け取る。
    """
    import systems.thermal.analyses as module  # noqa: PLC0415  lazy（上記 NOTE 参照）

    return module


# ─── 合成入力ヘルパ ────────────────────────────────────────────────────────────


def _thermalmodel(**overrides):
    base = {
        "body_size_x_m": 0.1,
        "body_size_y_m": 0.2263,
        "body_size_z_m": 0.366,
        "panel_thickness_m": 0.002,
        "panel_density_kg_m3": 2700.0,
        "panel_specific_heat_j_kg_k": 900.0,
        "node_specific_heat_j_kg_k": 800.0,
        "node_conductance_w_k": 0.5,
        "beta_angle_deg": 0.0,
        "time_step_s": 5.0,
        "initial_temperature_c": 20.0,
        "settle_orbits": 1,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakePanelSurfaces:
    """panel_surfaces[key].spec.absorptivity/emissivity を返す最小スタブ。"""

    def __init__(self):
        self._d = {
            "body_px_mx": SimpleNamespace(absorptivity=0.20, emissivity=0.85),
            "body_py_my": SimpleNamespace(absorptivity=0.20, emissivity=0.85),
            "body_pz_mz": SimpleNamespace(absorptivity=0.30, emissivity=0.85),
        }

    def __getitem__(self, key):
        return SimpleNamespace(spec=self._d[key])


def _component(*, mass_kg=0.5, power_w=5.0, face="MY", modes=None, tmin=None, tmax=None, qty=1):
    """1 コンポインスタンス相当の合成オブジェクト。"""
    if modes is None:
        modes = {"imaging": True}
    spec_kwargs = {
        "mass_kg": mass_kg,
        "power_per_unit_w": power_w,
    }
    if tmin is not None:
        spec_kwargs["temp_min_c"] = tmin
    if tmax is not None:
        spec_kwargs["temp_max_c"] = tmax
    placement = SimpleNamespace(face=face) if face is not None else None
    design = SimpleNamespace(quantity=qty, power_modes=dict(modes), placement=placement)
    return SimpleNamespace(spec=SimpleNamespace(**spec_kwargs), design=design)


def _loads(*instances):
    """run_analysis の loads（{plural: Table}）に相当する dict を作る。

    Table は values() を持てば良い（iter_instances が values() を呼ぶ）。
    """
    return {"fakes": SimpleNamespace(values=lambda: list(instances))}


# ─── 公開 @analysis（実データ・veriq 経由）─────────────────────────────────────


def test_thermal_node_temps_returns_dict_of_ranges(ta):
    """thermal_node_temps（transient calc）が {ノード名: (min, max)} の dict を返す。"""
    node_temps = run_analysis("thermal", "thermal_node_temps", {}).value
    assert isinstance(node_temps, dict)
    assert node_temps, "node_temps should not be empty"
    # 6 外面ノードを含む。
    assert {"PX", "MX", "PY", "MY", "PZ", "MZ"} <= set(node_temps)
    # NOTE: veriq は結果を tree に round-trip する際 tuple を list に変換するため、
    # 値は (min, max) の 2 要素シーケンス（tuple or list）として受け取る。
    for name, rng in node_temps.items():
        assert isinstance(rng, list | tuple) and len(rng) == 2, name
        lo, hi = rng
        assert lo <= hi, name
    # 少なくとも 1 つはコンポノード（外面・MLI 以外）を含む。
    assert ta._component_node_ranges(node_temps), "expected at least one component node"


def test_scalars_match_thermal_node_temps(ta):
    """scalar @analysis が thermal_node_temps から正しく min/max を抽出する。"""
    node_temps = run_analysis("thermal", "thermal_node_temps", {}).value
    comp = ta._component_node_ranges(node_temps)
    expected_max = max(hi for _, hi in comp.values())
    expected_min = min(lo for lo, _ in comp.values())
    assert run_analysis("thermal", "max_component_temp_c", {}).value == pytest.approx(expected_max)
    assert run_analysis("thermal", "min_component_temp_c", {}).value == pytest.approx(expected_min)

    rng = ta._battery_range(node_temps)
    if rng is not None:
        assert run_analysis("thermal", "battery_min_temp_c", {}).value == pytest.approx(rng[0])
        assert run_analysis("thermal", "battery_max_temp_c", {}).value == pytest.approx(rng[1])


def test_battery_temps_in_reasonable_range(ta):
    """battery_min/max_temp_c が妥当な範囲（-40〜80 degC）に収まる。"""
    lo = run_analysis("thermal", "battery_min_temp_c", {}).value
    hi = run_analysis("thermal", "battery_max_temp_c", {}).value
    assert isinstance(lo, float)
    assert isinstance(hi, float)
    assert lo <= hi
    assert -40.0 <= lo <= 80.0
    assert -40.0 <= hi <= 80.0


def test_component_temp_extents_finite_and_ordered(ta):
    """min/max_component_temp_c が有限で min <= max。"""
    lo = run_analysis("thermal", "min_component_temp_c", {}).value
    hi = run_analysis("thermal", "max_component_temp_c", {}).value
    assert np.isfinite(lo)
    assert np.isfinite(hi)
    assert lo <= hi


def test_verify_returns_bool(ta):
    """verify_components_within_temp_limits は bool を返す（範囲判定が成立）。"""
    val = run_analysis("thermal", "verify_components_within_temp_limits", {}).value
    assert isinstance(val, bool)


# ─── 6 面マップ ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("face", "expected"),
    [
        ("PX", "PX"),
        ("MZ", "MZ"),
        ("C", "PZ"),
        ("CY+", "PY"),
        ("CY-", "MY"),
        ("CX+", "PX"),
        ("CZ-", "MZ"),
    ],
)
def test_non_standard_face_maps_to_box_face(ta, face, expected):
    """非標準 face（円筒系 / "C"）が機体 6 面のいずれかにマップされる。"""
    inst = _component(face=face)
    assert ta._mapped_face(inst) in {"PX", "MX", "PY", "MY", "PZ", "MZ"}
    assert ta._mapped_face(inst) == expected


def test_missing_face_falls_back_to_pz(ta):
    """placement / face が無いコンポは天頂 PZ にフォールバックする。"""
    inst = _component(face=None)
    assert ta._mapped_face(inst) == "PZ"


# ─── power_modes による発熱反映 ───────────────────────────────────────────────


def test_heat_on_raises_node_temperature_vs_off(ta):
    """同一コンポでも、当該モードで power ON のほうが OFF より高温になる。"""
    tm = _thermalmodel()
    ps = _FakePanelSurfaces()

    hot = _component(mass_kg=0.5, power_w=20.0, face="MY", modes={"imaging": True})
    cold = _component(mass_kg=0.5, power_w=20.0, face="MY", modes={"imaging": False})

    res_hot = ta._run_all_modes(_loads(hot), tm, ps, altitude_km=410.0)
    res_cold = ta._run_all_modes(_loads(cold), tm, ps, altitude_km=410.0)

    comp_hot = ta._component_node_ranges(res_hot)
    comp_cold = ta._component_node_ranges(res_cold)
    assert comp_hot, "hot config should produce a component node"
    assert comp_cold, "cold config should produce a component node"

    hot_max = max(hi for _, hi in comp_hot.values())
    cold_max = max(hi for _, hi in comp_cold.values())
    assert hot_max > cold_max


def test_build_config_creates_six_surfaces_and_component_nodes(ta):
    """_build_config は 6 外面 + 各コンポノードを持つ config を返す。"""
    tm = _thermalmodel()
    ps = _FakePanelSurfaces()
    loads = _loads(_component(face="PY"), _component(face="MZ"))
    cfg = ta._build_config(loads, tm, ps, mode="imaging")
    assert len(cfg.surfaces) == 6
    assert {s.name for s in cfg.surfaces} == {"PX", "MX", "PY", "MY", "PZ", "MZ"}
    assert len(cfg.internal_panels) == 2
    # 発熱が internal_heat_w に載っている。
    assert any(p.internal_heat_w > 0.0 for p in cfg.internal_panels)


def test_zero_mass_zero_heat_component_is_skipped(ta):
    """質量 0・発熱 0（純パッシブ）のコンポはノード化されない。"""
    tm = _thermalmodel()
    ps = _FakePanelSurfaces()
    passive = _component(mass_kg=0.0, power_w=0.0, face="PX", modes={"imaging": False})
    cfg = ta._build_config(_loads(passive), tm, ps, mode="imaging")
    assert len(cfg.internal_panels) == 0


def test_zero_mass_heater_gets_heat_capacity_floor(ta):
    """質量 0 でも発熱があるヒータ相当はノード化され、熱容量に下限ガードが効く。"""
    tm = _thermalmodel()
    ps = _FakePanelSurfaces()
    heater = _component(mass_kg=0.0, power_w=2.88, face="MY", modes={"imaging": True})
    cfg = ta._build_config(_loads(heater), tm, ps, mode="imaging")
    assert len(cfg.internal_panels) == 1
    assert cfg.internal_panels[0].heat_capacity_j_k >= 1.0


# ─── verify の bool 判定（合成入力で範囲内/外）─────────────────────────────────


def test_verify_helper_true_when_in_range(ta):
    """温度範囲が十分広いコンポは範囲内 → 判定対象が全て pass。"""
    tm = _thermalmodel()
    ps = _FakePanelSurfaces()
    inst = _component(
        mass_kg=2.0,
        power_w=2.0,
        face="MY",
        modes={"imaging": True},
        tmin=-100.0,
        tmax=200.0,
    )
    loads = _loads(inst)
    node_temps = ta._run_all_modes(loads, tm, ps, altitude_km=410.0)
    out_of_range = False
    for node_name, comp in ta._iter_thermal_nodes(loads):
        spec = comp.spec
        lo, hi = node_temps[node_name]
        if lo < spec.temp_min_c or hi > spec.temp_max_c:
            out_of_range = True
    assert out_of_range is False


def test_verify_helper_false_when_limits_too_tight(ta):
    """温度範囲を意図的に狭くしたコンポは範囲外 → False を導く。"""
    tm = _thermalmodel()
    ps = _FakePanelSurfaces()
    inst = _component(
        mass_kg=0.3,
        power_w=30.0,
        face="MZ",
        modes={"imaging": True},
        tmin=19.9,
        tmax=20.1,
    )
    loads = _loads(inst)
    node_temps = ta._run_all_modes(loads, tm, ps, altitude_km=410.0)
    out_of_range = False
    for node_name, comp in ta._iter_thermal_nodes(loads):
        spec = comp.spec
        lo, hi = node_temps[node_name]
        if lo < spec.temp_min_c or hi > spec.temp_max_c:
            out_of_range = True
    assert out_of_range is True


def test_settle_orbits_is_honored(ta):
    """settle_orbits を増やすと初期過渡が落ち、結果が変わる（複数周回が効く）。

    1 周（コールドスタート）と複数周（周期定常近似・最終1周評価）で同一入力でも
    ノード温度域が変化することを確認する。発熱体は 1 周では初期 20℃ から動き
    切らないため、周回数で結果が一致しないはず。
    """
    ps = _FakePanelSurfaces()
    inst = _component(mass_kg=1.5, power_w=8.0, face="MZ", modes={"imaging": True})
    loads = _loads(inst)

    one = ta._run_all_modes(loads, _thermalmodel(settle_orbits=1), ps, altitude_km=410.0)
    multi = ta._run_all_modes(loads, _thermalmodel(settle_orbits=4), ps, altitude_km=410.0)

    assert one != multi, "settle_orbits を変えても結果が変わらない（パラメータ未反映）"
