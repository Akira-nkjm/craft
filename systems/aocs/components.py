"""aocs system components.

Source: SEIRIOS 子衛星 (shared drive: SEIRIOS)
  - SEIRIOS_コンポ管理シート / 子衛星1
  - 電源モード検討 / 子衛星電力消費
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    PowerConsuming,
    TemperatureSensitive,
    fld,
)


class SunSenser(Component, MultiInstance, PowerConsuming, Placeable):
    """太陽センサ。複数個搭載することが多いので MultiInstance。"""

    fov_deg: float = fld(ge=0, le=180, desc="視野角")

    class Design:
        pass


class ReactionWheel(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """リアクションホイール。三軸姿勢制御のメインアクチュエータ。"""

    max_torque_nms: float = fld(ge=0, unit="N*m", desc="最大トルク")
    max_momentum_nms: float = fld(ge=0, unit="N*m*s", desc="最大角運動量")

    class Design:
        pass


class MagneticTorquer(Component, MultiInstance, PowerConsuming, Placeable):
    """磁気トルカ。RW アンローディング・粗姿勢制御に使用。"""

    max_dipole_moment_am2: float = fld(ge=0, unit="A*m^2", desc="最大磁気モーメント")

    class Design:
        pass


class StarTracker(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """スタートラッカ。精三軸姿勢決定の主センサ。"""

    accuracy_arcsec: float = fld(ge=0, unit="arcsec", desc="姿勢決定精度（3σ）")
    fov_deg: float = fld(ge=0, le=180, unit="deg", desc="視野角")
    update_rate_hz: float = fld(ge=0, default=10.0, unit="Hz", desc="更新周波数")

    class Design:
        pass


class Gyroscope(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """ジャイロスコープ（精/粗）。姿勢決定の角速度センサ。"""

    bias_stability_deg_per_h: float = fld(ge=0, unit="deg/h", desc="バイアス安定度")
    grade: str = fld(default="fine", desc="精度等級: fine / coarse")

    class Design:
        pass


class Magnetometer(Component, MultiInstance, PowerConsuming, Placeable):
    """磁気センサ（外部）。粗姿勢決定・磁気環境計測。"""

    range_ut: float = fld(ge=0, unit="uT", desc="計測レンジ")
    noise_nt: float = fld(ge=0, default=0.0, unit="nT", desc="ノイズフロア")

    class Design:
        pass
