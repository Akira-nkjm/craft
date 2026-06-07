"""AOCS system analyses。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。

toolbox 注意: numpy を返す関数がある。verify の bool 返却は
`bool()` にキャストしてから返す（TOML 直列化のため）。
"""

from typing import Annotated

import veriq as vq
from toolbox.aocs.actuators import (
    mtq_torque_nm as tb_mtq_torque_nm,
)
from toolbox.aocs.actuators import (
    rw_momentum_capacity_nms as tb_rw_momentum_capacity_nms,
)
from toolbox.aocs.actuators import (
    rw_saturation_time_h as tb_rw_saturation_time_h,
)
from toolbox.aocs.disturbances import (
    aerodynamic_torque_nm as tb_aerodynamic_torque_nm,
)
from toolbox.aocs.disturbances import (
    gravity_gradient_torque_nm as tb_gravity_gradient_torque_nm,
)
from toolbox.constants import R_EARTH

from craft.schema import analysis


@analysis(
    desc="RW0003 の角運動量容量 [N·m·s]（I_rotor × ω_max）",
    imports=["aocs"],
)
def rw_momentum_capacity_nms(
    reaction_wheels: Annotated[vq.Table, vq.Ref("$.reaction_wheels")],
) -> float:
    """全 RW の最大蓄積角運動量容量 [N·m·s]（1 軸あたり）。

    toolbox.aocs.actuators.rw_momentum_capacity_nms を使用。
    orbit_radius = R_EARTH + 410e3 m（ONGLAISAT 410 km 軌道）。

    NOTE: system="aocs" で登録するため imports=["aocs"] を指定。
    """
    if not reaction_wheels:
        return 0.0
    rw = next(iter(reaction_wheels.values()))
    inertia = rw.spec.rotor_inertia_kg_m2
    max_speed_rad_s = rw.spec.max_speed_rpm * (2.0 * 3.14159265358979 / 60.0)
    h = tb_rw_momentum_capacity_nms(inertia, max_speed_rad_s)
    return float(h)


@analysis(
    desc="MTQ SEIREN の平均発生トルク [N·m]（410 km 軌道, ±0.32 A·m², η_geom=0.5）",
    imports=["aocs"],
)
def mtq_available_torque_nm(
    magnetic_torquers: Annotated[vq.Table, vq.Ref("$.magnetic_torquers")],
) -> float:
    """MTQ が軌道平均で発生できるトルク [N·m]（双極子近似, η_geom=0.5）。

    toolbox.aocs.actuators.mtq_torque_nm を使用。
    orbit_radius = R_EARTH + 410e3 m（ONGLAISAT 410 km 軌道）。
    """
    if not magnetic_torquers:
        return 0.0
    mtq = next(iter(magnetic_torquers.values()))
    dipole = mtq.spec.max_dipole_moment_am2
    orbit_r = R_EARTH + 410e3  # [確定値] ONGLAISAT 410 km 軌道
    torque = tb_mtq_torque_nm(dipole, orbit_r, geom_efficiency=0.5)
    return float(torque)


@analysis(
    desc="重力傾斜外乱トルク [N·m]（ONGLAISAT 6U CubeSat, 410 km 軌道）",
    imports=["aocs"],
)
def gravity_gradient_disturbance_nm(
    reaction_wheels: Annotated[vq.Table, vq.Ref("$.reaction_wheels")],
) -> float:
    """重力傾斜外乱トルク [N·m]（最大主慣性差で保守評価）。

    toolbox.aocs.disturbances.gravity_gradient_torque_nm を使用。
    慣性は [S2E] satellite_structure.ini の確定値（衛星座標系・対角）:
      - Ixx = 0.151, Iyy = 0.164, Izz = 0.108 kg·m²
    重力傾斜は |I_max − I_min| に比例するため、最大差を取る軸ペア
    （Iyy = 0.164 を z 相当 / Izz = 0.108 を x 相当）で worst-case 評価する。
    attitude_error = 5 deg（worst-case 指向誤差）。
    """
    orbit_r = R_EARTH + 410e3  # [確定値] ONGLAISAT 410 km 軌道
    inertia_z = 0.164  # [S2E] 最大主慣性 Iyy [kg·m²]
    inertia_x = 0.108  # [S2E] 最小主慣性 Izz [kg·m²]
    attitude_error_rad = 5.0 * 3.14159265358979 / 180.0  # 5 deg worst-case
    torque = tb_gravity_gradient_torque_nm(
        orbit_radius_m=orbit_r,
        inertia_z_kg_m2=inertia_z,
        inertia_x_kg_m2=inertia_x,
        attitude_error_rad=attitude_error_rad,
    )
    return float(torque)


@analysis(
    desc="大気抵抗外乱トルク [N·m]（ONGLAISAT 6U CubeSat, 410 km 軌道）",
    imports=["aocs"],
)
def aerodynamic_disturbance_nm(
    reaction_wheels: Annotated[vq.Table, vq.Ref("$.reaction_wheels")],
) -> float:
    """大気抵抗外乱トルク [N·m]（保守推定）。

    toolbox.aocs.disturbances.aerodynamic_torque_nm を使用。
    410 km での大気密度: ~3e-11 kg/m³（NRLMSISE-00 中活動期）。
    衛星諸元:
      - reference_area = 0.02 m²（6U 側面 200cm² ≈ 0.02 m²）
      - drag_coefficient = 2.2（CubeSat 標準値）
      - cp_cg_offset = 0.05 m（推定 CP-CG オフセット）
    [推定] 全値推定。詳細 CAD 解析要。
    """
    orbit_r = R_EARTH + 410e3
    # 円軌道速度: v = sqrt(mu / r) ≈ 7.67 km/s
    import math

    from toolbox.constants import MU_EARTH

    v_orbital = math.sqrt(MU_EARTH / orbit_r)
    rho_410km = 3.0e-11  # [推定] 410 km 大気密度 [kg/m³]
    torque = tb_aerodynamic_torque_nm(
        atmospheric_density_kg_m3=rho_410km,
        orbital_velocity_m_s=v_orbital,
        drag_coefficient=2.2,
        reference_area_m2=0.02,
        cp_cg_offset_m=0.05,
    )
    return float(torque)


@analysis(
    desc="RW 単独の角運動量飽和時間 [h]（総外乱 = 重力傾斜 + 空気抵抗）",
    imports=["aocs"],
)
def rw_saturation_time_h(
    h_rw: Annotated[float, vq.Ref("@rw_momentum_capacity_nms")],
    t_gg: Annotated[float, vq.Ref("@gravity_gradient_disturbance_nm")],
    t_aero: Annotated[float, vq.Ref("@aerodynamic_disturbance_nm")],
) -> float:
    """RW が総 secular 外乱で飽和するまでの時間 [h]。

    低高度 410 km では空気抵抗外乱が支配的（重力傾斜の ~230 倍）。
    総外乱（重力傾斜 + 空気抵抗）を secular 外乱として飽和時間を計算する。
    LEO では通常 1 軌道未満で飽和するため、MTQ による定期 desat が前提。
    """
    total_disturbance_nm = t_gg + t_aero
    if total_disturbance_nm <= 0.0:
        return 0.0
    return float(
        tb_rw_saturation_time_h(
            rw_momentum_capacity_nms=h_rw,
            secular_disturbance_torque_nm=total_disturbance_nm,
            momentum_margin=0.2,  # 20% マージン
        )
    )


@analysis(
    verify=True,
    desc="MTQ が総外乱（重力傾斜+空気抵抗）に対し RW を desat できるトルク余裕を持つか",
    imports=["aocs"],
)
def verify_mtq_can_desaturate_rw(
    t_mtq: Annotated[float, vq.Ref("@mtq_available_torque_nm")],
    t_gg: Annotated[float, vq.Ref("@gravity_gradient_disturbance_nm")],
    t_aero: Annotated[float, vq.Ref("@aerodynamic_disturbance_nm")],
) -> bool:
    """MTQ の発生トルクが総 secular 外乱（重力傾斜 + 空気抵抗）を上回るか。

    LEO（410 km）では空気抵抗が支配的で RW は 1 軌道未満で飽和するため、
    AOCS 成立条件は「RW 単独保持」ではなく「**MTQ が外乱以上のトルクで RW を
    定期 desat できる**」こと。MTQ 平均トルク >= 総外乱 × (1 + 20% margin) で OK。
    """
    total_disturbance_nm = t_gg + t_aero
    if t_mtq <= 0.0:
        return False
    return t_mtq >= total_disturbance_nm * 1.2
