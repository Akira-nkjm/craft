"""C&DH subsystem components — Singleton 例。"""

from schema import Component, PowerConsuming, TemperatureSensitive, fld


class OBC(Component, PowerConsuming, TemperatureSensitive):
    """On-Board Computer。中心計算機、1 機構成（default Singleton）。"""

    clock_mhz: int = fld(ge=0, unit="MHz")
    ram_mb: int = fld(ge=0, unit="MB")
    storage_gb: float = fld(ge=0, unit="GB")
    architecture: str = fld(desc="CPU アーキ (ARM/RISC-V 等)")

    class Design:
        firmware_version: str = fld(default="")
        boot_partition_count: int = fld(ge=1, default=2)

    class Requirements:
        mtbf_hours: float = fld(ge=0, default=50000, unit="h")
        radiation_tolerance_krad: float = fld(ge=0, default=20, unit="krad")
