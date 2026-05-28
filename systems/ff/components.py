"""Formation Flying system components.

Source: SEIRIOS 子衛星 (shared drive: SEIRIOS)
  - SEIRIOS_コンポ管理シート / 子衛星1 FF / FF/AOCS セクション
  - 電源モード検討 / 子衛星電力消費 行 19-22
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    PowerConsuming,
    TemperatureSensitive,
    fld,
)


class GNSSReceiver(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """GNSS 受信機。子-親相対航法（CDGNSS）に使用。"""

    constellation: str = fld(default="GPS+Galileo", desc="対応コンステレーション")
    channel_count: int = fld(ge=1, default=12, desc="チャンネル数")
    update_rate_hz: float = fld(ge=0, default=10.0, unit="Hz", desc="更新周波数")

    class Design:
        pass


class GNSSAntenna(Component, MultiInstance, Placeable):
    """GNSS アンテナ。"""

    band: str = fld(default="L1+L2", desc="対応バンド")
    gain_dbi: float = fld(default=0.0, unit="dBi")

    class Design:
        pass


class OpticalLED(Component, MultiInstance, PowerConsuming, Placeable):
    """光学航法用 LED。親衛星からの相対計測ターゲット。"""

    wavelength_nm: float = fld(ge=0, default=850.0, unit="nm", desc="ピーク波長")
    optical_power_w: float = fld(ge=0, default=0.0, unit="W", desc="光出力")
    beam_angle_deg: float = fld(ge=0, le=180, default=30.0, unit="deg", desc="ビーム角")

    class Design:
        pass


class OpticalMirror(Component, MultiInstance, Placeable):
    """光学反射ミラー。レーザー距離計のリトロリフレクタ。"""

    reflectivity: float = fld(ge=0, le=1, default=0.9, desc="反射率")
    diameter_mm: float = fld(ge=0, default=0.0, unit="mm", desc="有効径")
    mirror_type: str = fld(default="corner_cube", desc="ミラー種別: corner_cube / flat 等")

    class Design:
        pass


class FFController(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """FF 制御計算機（FF OBC）。"""

    clock_mhz: int = fld(ge=0, default=100, unit="MHz")
    ram_mb: int = fld(ge=0, default=256, unit="MB")
    storage_gb: float = fld(ge=0, default=8.0, unit="GB")

    class Design:
        pass
