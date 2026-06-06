"""Communication system components.

注意: `from __future__ import annotations` は書かない（veriq の inspect.signature を壊す）。
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
    """送受信機。S-band / X-band / LoRa などをカバーする汎用クラス。

    ONGLAISAT: SRx（S uplink）, STx（S downlink）, XTx（X downlink）,
    LoRa S&F を同一モデルで扱う。
    """

    band: str = fld(desc="周波数帯: bluetooth / s_band / lora / x_band 等")
    direction: str = fld(default="tx_rx", desc="tx / rx / tx_rx")
    frequency_mhz: float = fld(ge=0, default=0.0, unit="MHz", desc="中心周波数")
    tx_power_w: float = fld(ge=0, default=0.0, unit="W", desc="送信電力")
    data_rate_kbps: float = fld(ge=0, default=0.0, unit="kbps", desc="データレート")
    s2e_data_rate_kbps: float = fld(ge=0, default=0.0, unit="kbps", desc="S2E 設定レート")
    max_data_rate_kbps: float = fld(ge=0, default=0.0, unit="kbps", desc="最大データレート")
    modulation: str = fld(default="", desc="変調方式")
    tx_gain_dbi: float = fld(default=0.0, unit="dBi", desc="衛星送信アンテナ利得")
    rx_gain_dbi: float = fld(default=0.0, unit="dBi", desc="衛星受信アンテナ利得")
    tx_loss_feeder_db: float = fld(default=0.0, unit="dB", desc="衛星送信フィーダ損失")
    tx_loss_pointing_db: float = fld(default=0.0, unit="dB", desc="衛星送信ポインティング損失")
    rx_loss_feeder_db: float = fld(default=0.0, unit="dB", desc="衛星受信フィーダ損失")
    rx_loss_pointing_db: float = fld(default=0.0, unit="dB", desc="衛星受信ポインティング損失")
    rx_system_noise_temperature_k: float = fld(
        ge=0,
        default=0.0,
        unit="K",
        desc="衛星受信系雑音温度",
    )
    ground_tx_power_w: float = fld(ge=0, default=0.0, unit="W", desc="地上局送信電力")
    ground_tx_gain_dbi: float = fld(default=0.0, unit="dBi", desc="地上局送信利得")
    ground_rx_gain_dbi: float = fld(default=0.0, unit="dBi", desc="地上局受信利得")
    ground_loss_feeder_db: float = fld(default=0.0, unit="dB", desc="地上局フィーダ損失")
    ground_loss_pointing_db: float = fld(default=0.0, unit="dB", desc="地上局ポインティング損失")
    ground_rx_system_noise_temperature_k: float = fld(
        ge=0,
        default=0.0,
        unit="K",
        desc="地上局受信系雑音温度",
    )
    atmospheric_loss_db: float = fld(default=0.0, unit="dB", desc="大気損失")
    rainfall_loss_db: float = fld(default=0.0, unit="dB", desc="降雨損失")
    polarization_loss_db: float = fld(default=0.0, unit="dB", desc="偏波損失")
    other_loss_db: float = fld(default=0.0, unit="dB", desc="その他損失")
    required_ebn0_db: float = fld(default=0.0, unit="dB", desc="要求 Eb/N0")
    hardware_deterioration_db: float = fld(default=0.0, unit="dB", desc="ハードウェア劣化")
    coding_gain_db: float = fld(default=0.0, unit="dB", desc="符号化利得（負値で要求低減）")
    margin_requirement_db: float = fld(default=0.0, unit="dB", desc="要求リンクマージン")
    pass_duration_s: float = fld(ge=0, default=0.0, unit="s", desc="1 パス可視時間")
    link_efficiency: float = fld(ge=0, le=1, default=0.9, desc="リンク実効効率")

    class Design:
        pass


class Antenna(Component, MultiInstance, Placeable):
    """アンテナ。Transceiver と対で使用する受動コンポ。"""

    band: str = fld(desc="対応周波数帯: s_band / lora / bluetooth 等")
    gain_dbi: float = fld(default=0.0, unit="dBi", desc="アンテナ利得")
    polarization: str = fld(default="LHCP", desc="偏波: LHCP / RHCP / Linear")
    direction: str = fld(default="tx_rx", desc="tx / rx / tx_rx")
    linked_transceiver: str = fld(default="", desc="対応 Transceiver インスタンス名")
    radiation_pattern: str = fld(default="", desc="放射パターン CSV 等")

    class Design:
        pass
