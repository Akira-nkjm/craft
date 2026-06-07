"""Comm system analyses。

veriq 制約: scope に貼られる calculation / verification の引数は全て
`Annotated[..., vq.Ref(...)]` であること。生のパラメータが必要なら
`system=None` で ad-hoc 化する。
"""

from typing import Annotated

import veriq as vq
from toolbox.comm.data import data_volume_per_pass_mb as tb_data_volume_per_pass_mb
from toolbox.comm.link import cn0_dbhz as tb_cn0_dbhz
from toolbox.comm.link import eirp_dbw as tb_eirp_dbw
from toolbox.comm.link import fspl_db as tb_fspl_db
from toolbox.comm.link import g_over_t_db_k as tb_g_over_t_db_k
from toolbox.comm.link import link_margin_db as tb_link_margin_db
from toolbox.orbital.access import slant_range_km as tb_slant_range_km

from craft.schema import analysis

# 地上局の最小運用仰角 [deg]。仰角が低いほどスラントレンジが伸び（最悪）マージンが減る。
# S 帯 TT&C は低仰角でも成立、X 帯高速回線は仰角を確保する運用 → 別値で保守評価。
# [推定] 実運用の最小仰角は資料未確認（TBD）。
_MIN_ELEVATION_SBAND_DEG = 5.0
_MIN_ELEVATION_XBAND_DEG = 10.0


def _loss_db(value: float) -> float:
    """S2E ini は損失を負値で持つため、toolbox 入力用に損失量へ直す。"""
    return abs(value)


def _effective_required_ebn0_db(transceiver) -> float:
    return (
        transceiver.spec.required_ebn0_db
        + transceiver.spec.hardware_deterioration_db
        + transceiver.spec.coding_gain_db
    )


def _downlink_margin_db(transceiver, distance_km: float, data_rate_kbps: float = 0.0) -> float:
    # data_rate_kbps=0 のとき transceiver の設計レートを使用。明示時はそのレートで評価。
    rate_kbps = data_rate_kbps if data_rate_kbps > 0.0 else transceiver.spec.data_rate_kbps
    eirp_dbw = tb_eirp_dbw(
        transmit_power_w=transceiver.spec.tx_power_w,
        transmit_gain_db=transceiver.spec.tx_gain_dbi,
        feed_loss_db=_loss_db(transceiver.spec.tx_loss_feeder_db),
        pointing_loss_db=_loss_db(transceiver.spec.tx_loss_pointing_db),
    )
    ground_g_over_t_db_k = tb_g_over_t_db_k(
        receive_gain_db=transceiver.spec.ground_rx_gain_dbi,
        feed_loss_db=_loss_db(transceiver.spec.ground_loss_feeder_db),
        pointing_loss_db=_loss_db(transceiver.spec.ground_loss_pointing_db),
        system_noise_temp_k=transceiver.spec.ground_rx_system_noise_temperature_k,
    )
    propagation_loss_db = tb_fspl_db(
        distance_km=distance_km,
        frequency_ghz=transceiver.spec.frequency_mhz / 1000.0,
    )
    total_loss_db = (
        propagation_loss_db
        + _loss_db(transceiver.spec.atmospheric_loss_db)
        + _loss_db(transceiver.spec.rainfall_loss_db)
        + _loss_db(transceiver.spec.polarization_loss_db)
        + _loss_db(transceiver.spec.other_loss_db)
    )
    cn0_dbhz = tb_cn0_dbhz(
        eirp_dbw=eirp_dbw,
        g_over_t_db_k=ground_g_over_t_db_k,
        total_loss_db=total_loss_db,
    )
    return tb_link_margin_db(
        cn0_dbhz=cn0_dbhz,
        data_rate_bps=rate_kbps * 1000.0,
        required_ebn0_db=_effective_required_ebn0_db(transceiver),
    )


def _uplink_margin_db(transceiver, distance_km: float) -> float:
    ground_eirp_dbw = tb_eirp_dbw(
        transmit_power_w=transceiver.spec.ground_tx_power_w,
        transmit_gain_db=transceiver.spec.ground_tx_gain_dbi,
        feed_loss_db=_loss_db(transceiver.spec.ground_loss_feeder_db),
        pointing_loss_db=_loss_db(transceiver.spec.ground_loss_pointing_db),
    )
    sat_g_over_t_db_k = tb_g_over_t_db_k(
        receive_gain_db=transceiver.spec.rx_gain_dbi,
        feed_loss_db=_loss_db(transceiver.spec.rx_loss_feeder_db),
        pointing_loss_db=_loss_db(transceiver.spec.rx_loss_pointing_db),
        system_noise_temp_k=transceiver.spec.rx_system_noise_temperature_k,
    )
    propagation_loss_db = tb_fspl_db(
        distance_km=distance_km,
        frequency_ghz=transceiver.spec.frequency_mhz / 1000.0,
    )
    total_loss_db = (
        propagation_loss_db
        + _loss_db(transceiver.spec.atmospheric_loss_db)
        + _loss_db(transceiver.spec.rainfall_loss_db)
        + _loss_db(transceiver.spec.polarization_loss_db)
        + _loss_db(transceiver.spec.other_loss_db)
    )
    cn0_dbhz = tb_cn0_dbhz(
        eirp_dbw=ground_eirp_dbw,
        g_over_t_db_k=sat_g_over_t_db_k,
        total_loss_db=total_loss_db,
    )
    return tb_link_margin_db(
        cn0_dbhz=cn0_dbhz,
        data_rate_bps=transceiver.spec.data_rate_kbps * 1000.0,
        required_ebn0_db=_effective_required_ebn0_db(transceiver),
    )


@analysis(
    desc="モード別 通信系消費電力 [W]",
    imports=["mission"],
)
def comm_power_per_mode_w(
    transceivers: Annotated[vq.Table, vq.Ref("$.transceivers")],
    mode_configs: Annotated[vq.Table, vq.Ref("$.operation_mode_configs", scope="mission")],
) -> dict[str, float]:
    """各運用モードにおける Transceiver 消費電力合計 [W]。"""
    result: dict[str, float] = {}
    for mode_name in mode_configs:
        result[mode_name] = sum(
            t.spec.power_per_unit_w
            for t in transceivers.values()
            if t.design.power_modes.get(mode_name, False)
        )
    return result


@analysis(
    desc="S帯 TT&C リンクマージン [dB]（SRx uplink / STx downlink, 高度=orbital 参照）",
    imports=["orbital"],
)
def sband_link_margins_db(
    transceivers: Annotated[vq.Table, vq.Ref("$.transceivers")],
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
) -> dict[str, float]:
    """最小仰角での最大スラントレンジにおける S-band uplink/downlink マージン [dB]。

    地上局リンクの距離は高度ではなく仰角依存のスラントレンジ。最小仰角
    （最悪条件 = 最長距離）で評価する。高度は orbital.altitude_km を参照。
    """
    slant_km = float(tb_slant_range_km(altitude_km, _MIN_ELEVATION_SBAND_DEG))
    return {
        "srx_uplink": float(_uplink_margin_db(transceivers["srx"], slant_km)),
        "stx_downlink": float(_downlink_margin_db(transceivers["stx"], slant_km)),
    }


@analysis(
    desc="X帯ダウンリンクマージン [dB]（S2E フライトレート 10Mbps, 高度=orbital 参照）",
    imports=["orbital"],
)
def xband_downlink_margin_db(
    transceivers: Annotated[vq.Table, vq.Ref("$.transceivers")],
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
) -> float:
    """最小仰角での最大スラントレンジにおける X-band downlink マージン [dB]。

    リンク成立判定は **S2E フライト設定レート（s2e_data_rate_kbps, 10 Mbps）**で評価する。
    36 Mbps はピーク能力（高仰角・短距離限定）で別途 data に併記。高度は orbital を参照。
    """
    xtx = transceivers["xtx"]
    slant_km = float(tb_slant_range_km(altitude_km, _MIN_ELEVATION_XBAND_DEG))
    return float(_downlink_margin_db(xtx, slant_km, data_rate_kbps=xtx.spec.s2e_data_rate_kbps))


@analysis(
    verify=True,
    desc="X帯ダウンリンクマージン（フライトレート）が要求 margin_requirement_db を満たすか",
)
def verify_xband_link_margin(
    transceivers: Annotated[vq.Table, vq.Ref("$.transceivers")],
    margin_db: Annotated[float, vq.Ref("@xband_downlink_margin_db")],
) -> bool:
    """X帯リンクマージン（S2E フライトレート 10Mbps）が要求値以上か。

    要求は xtx.spec.margin_requirement_db（[S2E]）。36 Mbps ピークは別評価。
    """
    required_db = transceivers["xtx"].spec.margin_requirement_db
    return margin_db >= required_db


@analysis(desc="X帯 1 パスあたりダウンリンク容量 [MB/pass]（toolbox.comm.data）")
def xband_data_volume_per_pass_mb(
    transceivers: Annotated[vq.Table, vq.Ref("$.transceivers")],
) -> float:
    """XTx の設計レート・可視時間・リンク効率から 1 パス容量を見積もる。"""
    xtx = transceivers["xtx"]
    return tb_data_volume_per_pass_mb(
        data_rate_bps=xtx.spec.data_rate_kbps * 1000.0,
        pass_duration_s=xtx.spec.pass_duration_s,
        link_efficiency=xtx.spec.link_efficiency,
    )
