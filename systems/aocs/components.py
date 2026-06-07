"""aocs system components.

注意: `from __future__ import annotations` は書かない（veriq の inspect.signature を壊す）。

Source: ONGLAISAT AOCS — S2E ini ファイル / ONGLAISAT 質量表
  - 99_Sources/raw/s2e-aobc-initialize_files/components/{sagitta,stim210,nanossoc_d60,
    rm3100_aobc,rm3100_external,rw0003,mtq_seiren,mpu9250,oem7600}.ini
  - 99_Sources/raw/mass_inertia_breakdown.csv (「5.AOCS」行)

NOTE: ff system にも GNSSReceiver / GNSSAntenna が定義されているため、
  aocs 側の plural を "aocs_gnss_receivers" / "aocs_gnss_antennas" として衝突を回避。
  ff system 削除後は plural を "gnss_receivers" / "gnss_antennas" に戻すこと（TBD）。
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
    """太陽センサ。ONGLAISAT: nanoSSOC-D60 (Solar MEMS) × 4（PY/MY/PZ/MZ 面）。

    2軸デジタル太陽センサ。FOV ±60deg、粗姿勢決定・太陽指向の主センサ。
    [S2E] 消費電力・FOV は s2e-aobc-initialize_files/components/nanossoc_d60.ini より。
    [確定値] 質量 6.7 g/個 は mass_inertia_breakdown.csv (5.AOCS) より。
    """

    fov_deg: float = fld(ge=0, le=180, unit="deg", desc="視野角（半角）")

    class Design:
        pass


class ReactionWheel(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """リアクションホイール。ONGLAISAT: RW0003 (Sinclair/Rocket Lab) × 3（3軸直交配置）。

    精密姿勢制御 (fine_three_axis / imaging / xband_downlink) のメインアクチュエータ。
    蓄積角運動量は MTQ SEIREN によりアンローディング。
    [S2E] 全物理パラメータは rw0003.ini より（3台共通値）。
    """

    max_torque_nms: float = fld(ge=0, unit="N*m", desc="最大出力トルク")
    max_momentum_nms: float = fld(ge=0, unit="N*m*s", desc="角運動量容量（ω_max × I_rotor）")
    rotor_inertia_kg_m2: float = fld(
        ge=0, unit="kg*m^2", default=3.372e-6, desc="ロータ慣性モーメント [S2E rw0003.ini]"
    )
    max_speed_rpm: float = fld(
        ge=0, unit="rpm", default=8500.0, desc="最大回転速度 [S2E rw0003.ini]"
    )

    class Design:
        pass


class MagneticTorquer(Component, MultiInstance, PowerConsuming, Placeable):
    """磁気トルカ。ONGLAISAT: MTQ SEIREN (ISSL 設計) × 3軸。

    B-dot デタンブル・RW アンローディング（desaturation）に使用。
    [S2E] mtq_seiren.ini より。各軸 ±0.32 A·m² 対称レンジ。
    """

    max_dipole_moment_am2: float = fld(ge=0, unit="A*m^2", desc="最大磁気モーメント（片軸）")

    class Design:
        pass


class StarTracker(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """スタートラッカ。ONGLAISAT: Sagitta (Arcsec) × 1。

    精3軸絶対姿勢決定の主センサ。fine_three_axis / imaging / xband_downlink で使用。
    角速度 > 1 deg/s で捕捉不可 → デタンブル完了後に起動。
    [S2E] sagitta.ini より。視軸直交 ≈ 2 arcsec (3σ)、視軸 ≈ 10 arcsec。
    """

    accuracy_arcsec: float = fld(ge=0, unit="arcsec", desc="姿勢決定精度（視軸直交 3σ）")
    fov_deg: float = fld(ge=0, le=180, unit="deg", desc="視野角（半角）")
    update_rate_hz: float = fld(ge=0, default=5.0, unit="Hz", desc="更新周波数 [S2E prescaler=10]")
    sun_exclusion_deg: float = fld(ge=0, unit="deg", default=40.0, desc="太陽排他角（半角）")
    earth_exclusion_deg: float = fld(ge=0, unit="deg", default=30.0, desc="地球排他角（半角）")

    class Design:
        pass


class Gyroscope(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """ジャイロスコープ（精/粗）。ONGLAISAT: STIM210 (fine) × 1、MPU9250 (coarse) × 1。

    fine: STIM210 (Sensonor) — 精密姿勢決定、STT 更新間の角速度伝搬。
      ノイズ ≈ 4.36e-5 rad/s (≈ 0.0025 deg/s) [S2E stim210.ini]
    coarse: MPU9250 (InvenSense) — デタンブル・冗長系。9軸 IMU（gyro+mag+acc）内蔵。
      ノイズ ≈ 1.75e-3 rad/s（STIM210 比 ~40倍）[S2E mpu9250.ini]
    [S2E] stim210.ini / mpu9250.ini より。
    """

    bias_stability_deg_per_h: float = fld(ge=0, unit="deg/h", desc="バイアス安定度（1σ）")
    grade: str = fld(default="fine", desc="精度等級: fine / coarse")

    class Design:
        pass


class Magnetometer(Component, MultiInstance, PowerConsuming, Placeable):
    """磁気センサ。ONGLAISAT: RM3100 (PNI Sensor) × 2（内部 AOBC 基板 + 外部）。

    B-dot 制御・粗姿勢決定・RW アンローディングの磁場入力。
    外部ユニットは機体磁性体干渉を低減するため離隔搭載。
    [S2E] rm3100_aobc.ini / rm3100_external.ini より。ノイズ 15 nT (3σ/軸)。
    """

    range_ut: float = fld(ge=0, unit="uT", desc="計測レンジ")
    noise_nt: float = fld(ge=0, default=0.0, unit="nT", desc="ノイズフロア（3σ/軸）")

    class Design:
        pass


class GNSSReceiver(
    Component,
    MultiInstance,
    PowerConsuming,
    TemperatureSensitive,
    Placeable,
    plural="aocs_gnss_receivers",
):
    """GNSS 受信機。ONGLAISAT: NovAtel OEM7600（軌道・時刻決定）。

    位置・速度・時刻（PVT）を提供。撮像ターゲティング幾何計算・時刻同期に使用。
    fine_three_axis / imaging / xband_downlink で ON。
    [S2E] oem7600.ini より。gnss_id = GJ（GPS + QZSS/みちびき）、12 ch、1.0 W。

    plural="aocs_gnss_receivers" — ff.GNSSReceiver (gnss_receivers) との衝突を回避。
    ff system 削除後は plural="gnss_receivers" に戻すこと（TBD）。
    """

    constellation: str = fld(default="GPS+QZSS", desc="対応コンステレーション（S2E gnss_id=GJ）")
    channel_count: int = fld(ge=1, default=12, desc="同時追尾チャネル数 [S2E maximum_channel]")
    update_rate_hz: float = fld(
        ge=0, default=1.0, unit="Hz", desc="測位更新周波数（prescaler=100 → ~1 Hz）[S2E]"
    )
    position_noise_m: float = fld(
        ge=0, unit="m", default=1.5, desc="位置ノイズ標準偏差（ECI）[S2E white_noise_std=1.5 m]"
    )

    class Design:
        pass


class GNSSAntenna(Component, MultiInstance, Placeable, plural="aocs_gnss_antennas"):
    """GNSS アンテナ。ONGLAISAT: Tallysman TW1889/TW1829 GPS アンテナ。

    [確定値] 質量 37.05 g は mass_inertia_breakdown.csv (5.AOCS GPS-A 行) より。
    [S2E] antenna_half_width_deg = 60 (oem7600.ini)。

    plural="aocs_gnss_antennas" — ff.GNSSAntenna (gnss_antennas) との衝突を回避。
    """

    band: str = fld(default="L1+L2", desc="対応バンド")
    gain_dbi: float = fld(default=0.0, unit="dBi", desc="アンテナ利得（公称）")
    half_angle_deg: float = fld(
        ge=0, unit="deg", default=60.0, desc="アンテナ半値幅 [S2E antenna_half_width_deg=60]"
    )

    class Design:
        pass
