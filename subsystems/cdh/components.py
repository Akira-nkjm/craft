"""C&DH subsystem components — Singleton 例 + ネスト型 (A2) のデモ。"""

from pydantic import BaseModel

from schema import Component, PowerConsuming, TemperatureSensitive, fld


class BusInterface(BaseModel):
    """OBC のバス I/F 仕様。ネスト Pydantic model の例。"""

    voltage_v: float
    rated_current_a: float
    protocol: str = "CAN"


class OBC(Component, PowerConsuming, TemperatureSensitive):
    """On-Board Computer。中心計算機、1 機構成（default Singleton）。"""

    clock_mhz: int = fld(ge=0, unit="MHz")
    ram_mb: int = fld(ge=0, unit="MB")
    storage_gb: float = fld(ge=0, unit="GB")
    architecture: str = fld(desc="CPU アーキ (ARM/RISC-V 等)")
    bus_interface: BusInterface = fld(desc="バス I/F (ネスト model)")

    class Design:
        firmware_version: str = fld(default="")
        boot_partition_count: int = fld(ge=1, default=2)

    class Requirements:
        mtbf_hours: float = fld(ge=0, default=50000, unit="h")
        radiation_tolerance_krad: float = fld(ge=0, default=20, unit="krad")
