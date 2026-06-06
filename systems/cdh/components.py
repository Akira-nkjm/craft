"""C&DH system components.

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


class BusInterface(Component, MultiInstance, Placeable):
    """OBC 間・OBC-コンポーネント間の受動データバス／ポート群。

    ONGLAISAT: MOBC UART（RS-422 / LVTTL）を主バスとし、AOBC/TOBC 配下に
    I2C / SPI / GPIO / ADC のローカル I/F を持つ。
    """

    protocol: str = fld(desc="UART / I2C / SPI / GPIO / ADC / CCSDS 等")
    physical_layer: str = fld(default="", desc="RS-422 / RS-485 / LVTTL 等")
    port_count: int = fld(ge=0, default=0, desc="ポートまたはチャネル数")
    endpoint_count: int = fld(ge=0, default=0, desc="接続先ノード数")
    bandwidth_bps: float = fld(ge=0, default=0.0, unit="bit/s", desc="想定バス帯域")
    nominal_traffic_bps: float = fld(
        ge=0,
        default=0.0,
        unit="bit/s",
        desc="通常時の概算テレメトリ/コマンド流量",
    )
    master: str = fld(default="", desc="バスマスタまたは管理 OBC")

    class Design:
        pass

    class Requirements:
        max_utilization: float = fld(ge=0, le=1, default=0.5, desc="許容バス占有率")


class OBC(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """On-Board Computer。

    ONGLAISAT: MOBC（バスマスタ）/ AOBC（AOCS）/ TOBC（Thermal）の 3 OBC。
    """

    processor: str = fld(desc="CPU / MCU")
    clock_mhz: int = fld(ge=0, unit="MHz")
    ram_kb: int = fld(ge=0, unit="KiB", desc="内蔵+外部 RAM 容量")
    rom_kb: int = fld(ge=0, unit="KiB", desc="ROM / program flash 容量")
    architecture: str = fld(desc="CPU アーキ / heritage")
    nvm_kb: int = fld(ge=0, default=0, unit="KiB", desc="MRAM / FRAM 等 NVM 容量")
    storage_gb: float = fld(ge=0, default=0.0, unit="GB", desc="大容量データ保存領域")
    role: str = fld(default="", desc="衛星内での役割")
    primary_bus: str = fld(default="", desc="MOBC との主接続")
    nominal_packet_rate_hz: float = fld(
        ge=0,
        default=1.0,
        unit="Hz",
        desc="HK/制御テレメトリの概算パケット頻度",
    )
    nominal_packet_size_bits: float = fld(
        ge=0,
        default=2048.0,
        unit="bit",
        desc="HK/制御テレメトリの概算パケットサイズ",
    )

    class Design:
        firmware_version: str = fld(default="")
        boot_partition_count: int = fld(ge=1, default=1)
        estimated_wcet_s: float = fld(
            ge=0,
            default=0.0,
            unit="s",
            desc="主要周期処理の概算 WCET",
        )
        control_period_s: float = fld(
            gt=0,
            default=1.0,
            unit="s",
            desc="主要周期処理の周期",
        )

    class Requirements:
        mtbf_hours: float = fld(ge=0, default=50000, unit="h")
        radiation_tolerance_krad: float = fld(ge=0, default=20, unit="krad")
        max_cpu_utilization: float = fld(ge=0, le=1, default=0.7, desc="許容 CPU 占有率")
        max_no_contact_days: float = fld(
            ge=0,
            default=3.0,
            unit="d",
            desc="オンボード保存を要求する最大無通信日数",
        )
