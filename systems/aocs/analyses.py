"""AOCS system analyses。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。

toolbox 注意: numpy を返す関数がある。verify の bool 返却は
`bool()` にキャストしてから返す（TOML 直列化のため）。
"""

from typing import Annotated

import numpy as np
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
    max_speed_rad_s = rw.spec.max_speed_rpm * (2.0 * np.pi / 60.0)
    h = tb_rw_momentum_capacity_nms(inertia, max_speed_rad_s)
    return float(h)


@analysis(
    desc="MTQ SEIREN の平均発生トルク [N·m]（双極子近似, η_geom=0.5）",
    imports=["aocs", "orbital"],
)
def mtq_available_torque_nm(
    magnetic_torquers: Annotated[vq.Table, vq.Ref("$.magnetic_torquers")],
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
) -> float:
    """MTQ が軌道平均で発生できるトルク [N·m]（双極子近似, η_geom=0.5）。

    toolbox.aocs.actuators.mtq_torque_nm を使用。高度は orbital.altitude_km を参照。
    """
    if not magnetic_torquers:
        return 0.0
    mtq = next(iter(magnetic_torquers.values()))
    dipole = mtq.spec.max_dipole_moment_am2
    orbit_r = R_EARTH + altitude_km * 1000.0
    torque = tb_mtq_torque_nm(dipole, orbit_r, geom_efficiency=0.5)
    return float(torque)


@analysis(
    desc="重力傾斜外乱トルク [N·m]（高度=orbital, 慣性=mission.massproperties 参照）",
    imports=["aocs", "orbital", "mission"],
)
def gravity_gradient_disturbance_nm(
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
    iyy: Annotated[float, vq.Ref("$.massproperties.iyy_kg_m2", scope="mission")],
    izz: Annotated[float, vq.Ref("$.massproperties.izz_kg_m2", scope="mission")],
    pointing_error_deg: Annotated[float, vq.Ref("$.disturbancemodel.pointing_error_deg")],
) -> float:
    """重力傾斜外乱トルク [N·m]（最大主慣性差で保守評価）。

    高度は orbital、慣性（Iyy=最大 / Izz=最小）は mission.massproperties、指向誤差は
    aocs.disturbancemodel を参照。重力傾斜は |I_max − I_min| に比例するため最大差で評価。
    """
    orbit_r = R_EARTH + altitude_km * 1000.0
    attitude_error_rad = pointing_error_deg * np.pi / 180.0
    torque = tb_gravity_gradient_torque_nm(
        orbit_radius_m=orbit_r,
        inertia_z_kg_m2=iyy,
        inertia_x_kg_m2=izz,
        attitude_error_rad=attitude_error_rad,
    )
    return float(torque)


@analysis(
    desc="大気抵抗外乱トルク [N·m]（高度=orbital, 空力係数=aocs.disturbancemodel 参照）",
    imports=["aocs", "orbital"],
)
def aerodynamic_disturbance_nm(
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
    reference_area_m2: Annotated[float, vq.Ref("$.disturbancemodel.reference_area_m2")],
    drag_coefficient: Annotated[float, vq.Ref("$.disturbancemodel.drag_coefficient")],
    cp_cg_offset_m: Annotated[float, vq.Ref("$.disturbancemodel.cp_cg_offset_m")],
    rho_kg_m3: Annotated[float, vq.Ref("$.disturbancemodel.atmospheric_density_kg_m3")],
) -> float:
    """大気抵抗外乱トルク [N·m]（保守推定）。

    高度は orbital、空力係数（基準面積/抗力係数/CP-CG/大気密度）は
    aocs.disturbancemodel を参照。円軌道速度 v = sqrt(μ/r) で計算する。
    """
    import math

    from toolbox.constants import MU_EARTH

    orbit_r = R_EARTH + altitude_km * 1000.0
    v_orbital = math.sqrt(MU_EARTH / orbit_r)
    torque = tb_aerodynamic_torque_nm(
        atmospheric_density_kg_m3=rho_kg_m3,
        orbital_velocity_m_s=v_orbital,
        drag_coefficient=drag_coefficient,
        reference_area_m2=reference_area_m2,
        cp_cg_offset_m=cp_cg_offset_m,
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
    momentum_margin: Annotated[float, vq.Ref("$.disturbancemodel.momentum_margin")],
) -> float:
    """RW が総 secular 外乱で飽和するまでの時間 [h]。

    低高度 410 km では空気抵抗外乱が支配的（重力傾斜の ~230 倍）。
    総外乱（重力傾斜 + 空気抵抗）を secular 外乱として飽和時間を計算する。
    マージン率は aocs.disturbancemodel を参照。
    LEO では通常 1 軌道未満で飽和するため、MTQ による定期 desat が前提。
    """
    total_disturbance_nm = t_gg + t_aero
    if total_disturbance_nm <= 0.0:
        return 0.0
    return float(
        tb_rw_saturation_time_h(
            rw_momentum_capacity_nms=h_rw,
            secular_disturbance_torque_nm=total_disturbance_nm,
            momentum_margin=momentum_margin,
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
    momentum_margin: Annotated[float, vq.Ref("$.disturbancemodel.momentum_margin")],
) -> bool:
    """MTQ の発生トルクが総 secular 外乱（重力傾斜 + 空気抵抗）を上回るか。

    LEO（410 km）では空気抵抗が支配的で RW は 1 軌道未満で飽和するため、
    AOCS 成立条件は「RW 単独保持」ではなく「**MTQ が外乱以上のトルクで RW を
    定期 desat できる**」こと。MTQ 平均トルク >= 総外乱 × (1 + margin) で OK。
    マージン率は aocs.disturbancemodel を参照。
    """
    total_disturbance_nm = t_gg + t_aero
    if t_mtq <= 0.0:
        return False
    return t_mtq >= total_disturbance_nm * (1.0 + momentum_margin)
