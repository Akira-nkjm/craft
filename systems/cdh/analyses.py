"""C&DH system analyses。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。
"""

from typing import Annotated

import veriq as vq
from toolbox.cdh.data import daily_data_generation_mb as tb_daily_data_generation_mb
from toolbox.cdh.processing import (
    bus_utilization as tb_bus_utilization,
)
from toolbox.cdh.processing import (
    cpu_utilization_margin as tb_cpu_utilization_margin,
)
from toolbox.cdh.processing import (
    cpu_utilization_per_mode as tb_cpu_utilization_per_mode,
)
from toolbox.cdh.processing import (
    packet_data_rate_bps as tb_packet_data_rate_bps,
)
from toolbox.cdh.storage import storage_capacity_margin_mb as tb_storage_capacity_margin_mb
from toolbox.cdh.storage import storage_fill_at_max_outage_mb as tb_storage_fill_at_max_outage_mb

from craft.schema import analysis


@analysis(
    desc="モード別 C&DH OBC 消費電力 [W]（MOBC/AOBC/TOBC）",
    imports=["mission"],
)
def obc_power_per_mode_w(
    obcs: Annotated[vq.Table, vq.Ref("$.obcs")],
    mode_configs: Annotated[vq.Table, vq.Ref("$.operation_mode_configs", scope="mission")],
) -> dict[str, float]:
    """各運用モードにおける OBC 消費電力合計 [W]。"""
    result: dict[str, float] = {}
    for mode_name in mode_configs:
        result[mode_name] = sum(
            obc.spec.power_per_unit_w * obc.design.quantity
            for obc in obcs.values()
            if obc.design.power_modes.get(mode_name, False)
        )
    return result


@analysis(desc="C&DH OBC の CPU 占有率マージン [-]（toolbox.cdh.processing）")
def obc_cpu_margin(
    obcs: Annotated[vq.Table, vq.Ref("$.obcs")],
) -> dict[str, float]:
    """主要周期処理の WCET/period から OBC 別 CPU マージンを返す。"""
    margins: dict[str, float] = {}
    for name, obc in obcs.items():
        utilization = tb_cpu_utilization_per_mode(
            obc.design.estimated_wcet_s,
            obc.design.control_period_s,
        )
        margins[name] = tb_cpu_utilization_margin(
            obc.requirements.max_cpu_utilization,
            utilization,
        )
    return margins


@analysis(desc="C&DH データバス占有率マージン [-]（toolbox.cdh.processing）")
def bus_utilization_margin(
    bus_interfaces: Annotated[vq.Table, vq.Ref("$.bus_interfaces")],
) -> dict[str, float]:
    """受動バス別に、通常トラフィックに対する占有率マージンを返す。"""
    margins: dict[str, float] = {}
    for name, bus in bus_interfaces.items():
        if bus.spec.bandwidth_bps <= 0.0:
            margins[name] = 0.0
            continue
        utilization = tb_bus_utilization(
            bus.spec.nominal_traffic_bps,
            bus.spec.bandwidth_bps,
        )
        margins[name] = bus.requirements.max_utilization - utilization
    return margins


@analysis(desc="MOBC NAND の最大無通信時ストレージ容量マージン [MB]（toolbox.cdh.data/storage）")
def onboard_storage_margin_mb(
    obcs: Annotated[vq.Table, vq.Ref("$.obcs")],
) -> float:
    """OBC HK 生成量を MOBC NAND に保存する最悪無通信期間マージン [MB]。"""
    if not obcs:
        return 0.0

    packet_rate_bps = sum(
        tb_packet_data_rate_bps(
            obc.spec.nominal_packet_rate_hz,
            obc.spec.nominal_packet_size_bits,
        )
        * obc.design.quantity
        for obc in obcs.values()
    )
    daily_hk_mb = tb_daily_data_generation_mb(
        mission_data_rate_bps=0.0,
        mission_active_time_s=0.0,
        housekeeping_rate_bps=packet_rate_bps,
        housekeeping_active_time_s=86400.0,
    )
    no_contact_days = max(obc.requirements.max_no_contact_days for obc in obcs.values())
    stored_mb = tb_storage_fill_at_max_outage_mb(daily_hk_mb, no_contact_days)
    storage_capacity_mb = sum(
        obc.spec.storage_gb * 1000.0 * obc.design.quantity for obc in obcs.values()
    )
    return tb_storage_capacity_margin_mb(storage_capacity_mb, stored_mb)
