"""AOCS system configurations。

外乱解析（重力傾斜・空気抵抗）のモデルパラメータを data 駆動にするための config。
高度は orbital、慣性は mission.massproperties を参照し、ここには機体固有の
空力・指向モデル値（data.toml が single source）を置く。
"""

from craft.schema import Config, fld


class DisturbanceModel(Config):
    """姿勢外乱モデルのパラメータ（機体固有・推定値含む）。

    Source: 低高度 410 km の空力外乱モデル。reference_area / cp_cg_offset /
    atmospheric_density は [推定]（詳細 CAD / NRLMSISE-00 要）。
    drag_coefficient は CubeSat 標準値。
    """

    reference_area_m2: float = fld(
        ge=0, default=0.02, unit="m^2", desc="空力基準面積（6U 側面 ≈ 0.02 m²）[推定]"
    )
    drag_coefficient: float = fld(ge=0, default=2.2, desc="抗力係数（CubeSat 標準値）")
    cp_cg_offset_m: float = fld(ge=0, default=0.05, unit="m", desc="圧力中心-重心オフセット [推定]")
    atmospheric_density_kg_m3: float = fld(
        ge=0,
        default=3.0e-11,
        unit="kg/m^3",
        desc="軌道高度の大気密度（NRLMSISE-00 中活動期）[推定]",
    )
    pointing_error_deg: float = fld(
        ge=0, default=5.0, unit="deg", desc="重力傾斜評価用 worst-case 指向誤差"
    )
    momentum_margin: float = fld(ge=0, default=0.2, desc="RW 飽和/MTQ desat 判定のマージン率")
