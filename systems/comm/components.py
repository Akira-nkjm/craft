"""Communication system components.

Source: SEIRIOS 子衛星 (shared drive: SEIRIOS)
  - SEIRIOS_コンポ管理シート / 子衛星1 Comm セクション
  - 電源モード検討 / 子衛星電力消費 行 8-11
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    PowerConsuming,
    TemperatureSensitive,
    fld,
)


class Transceiver(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """送受信機。Bluetooth / S-band / LoRa などをカバーする汎用クラス。"""

    band: str = fld(desc="周波数帯: bluetooth / s_band / lora / x_band 等")
    direction: str = fld(default="tx_rx", desc="tx / rx / tx_rx")
    frequency_mhz: float = fld(ge=0, default=0.0, unit="MHz", desc="中心周波数")
    tx_power_w: float = fld(ge=0, default=0.0, unit="W", desc="送信電力")
    data_rate_kbps: float = fld(ge=0, default=0.0, unit="kbps", desc="データレート")
    modulation: str = fld(default="", desc="変調方式")

    class Design:
        pass


class Antenna(Component, MultiInstance, Placeable):
    """アンテナ。Transceiver と対で使用。"""

    band: str = fld(desc="対応周波数帯: s_band / lora / bluetooth 等")
    gain_dbi: float = fld(default=0.0, unit="dBi", desc="アンテナ利得")
    polarization: str = fld(default="LHCP", desc="偏波: LHCP / RHCP / Linear")
    direction: str = fld(default="tx_rx", desc="tx / rx / tx_rx")

    class Design:
        pass
