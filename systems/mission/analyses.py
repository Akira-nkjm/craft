"""Mission-level analyses（衛星全体ビュー + ペイロード解析）。

全 component 横断の集計は root model の `vq.Tag("Component")` と
analysis 引数の `vq.Collect` で受け取り、body では既存 aggregation helper に渡す。

ペイロード解析（toolbox.payload）:
  - pixel_gsd_m     : 画素 IFOV から GSD [m] を計算（toolbox.payload.imaging）
  - swath_width_km  : クロストラック スワス幅 [km]（toolbox.payload.imaging）
  - tdi_snr_factor  : TDI 積分段数による SNR 向上倍率（toolbox.payload.detector）
  - scene_data_volume_mbyte : 1 ミッションあたり画像データ量 [MB]（toolbox.payload.data）
"""

from typing import Annotated

import veriq as vq
from toolbox.payload.data import observation_data_volume_mbyte
from toolbox.payload.imaging import swath_width_m

from craft.analyses import total_mass_kg, total_quantity
from craft.schema import analysis


@analysis(desc="衛星全体の総質量 [kg]（コンポ + 構造体 + 推進剤）= wet mass 相当")
def total_bus_mass_kg(
    loads: Annotated[dict, vq.Collect(tag="Component")],
) -> float:
    """全 instance の spec.mass_kg × design.quantity を合算 [kg]。"""
    return total_mass_kg(*loads.values())


@analysis(desc="衛星全体の搭載コンポ個数（quantity 合計、debug 用）")
def total_component_count(
    loads: Annotated[dict, vq.Collect(tag="Component")],
) -> int:
    """全テーブルの quantity 合計。"""
    return total_quantity(*loads.values())


@analysis(desc="モデル積み上げ質量とフライト確定質量の差 [kg]（正 = モデルが軽い）")
def mass_budget_delta_kg(
    total_mass: Annotated[float, vq.Ref("@total_bus_mass_kg")],
    flight_mass_kg: Annotated[float, vq.Ref("$.missionprofile.flight_mass_kg")],
) -> float:
    """フライト確定質量 − モデル積み上げ質量 [kg]。未計上分の指標。

    基準値はハードコードせず `missionprofile.flight_mass_kg`（data.toml）を参照する。
    """
    return flight_mass_kg - total_mass


@analysis(
    verify=True,
    desc="モデル積み上げ質量がフライト確定質量と ±5% 以内で整合するか",
)
def verify_mass_budget_reconciled(
    total_mass: Annotated[float, vq.Ref("@total_bus_mass_kg")],
    flight_mass_kg: Annotated[float, vq.Ref("$.missionprofile.flight_mass_kg")],
) -> bool:
    """全機モデル質量がフライト確定質量（`missionprofile.flight_mass_kg`）と ±5% 以内か。

    構体系単体ではなく**全機の積み上げ**を data.toml の確定値と突き合わせる。
    出典 CSV 内訳は ~6.2kg しか積み上がらず、光学系内部等は推定で補完している。
    """
    if flight_mass_kg <= 0.0:
        return False
    return abs(total_mass - flight_mass_kg) / flight_mass_kg <= 0.05


# ─── ペイロード光学・撮像解析（telescope/image_sensors/orbital を data 参照）───


@analysis(
    desc="画素 IFOV から GSD [m]（光学=telescope, 高度=orbital 参照）",
    imports=["orbital"],
)
def pixel_gsd_m(
    pixel_size_m: Annotated[float, vq.Ref("$.telescope.spec.pixel_size_m")],
    focal_length_m: Annotated[float, vq.Ref("$.telescope.spec.focal_length_m")],
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
) -> float:
    """画素 IFOV（= pixel_size / focal_length）から地表 GSD [m] を返す。

    光学諸元は telescope、高度は orbital を参照（ハードコードしない）。
    ONGLAISAT: GSD = 410,000 × 5e-6 / 0.725 ≈ 2.828 m（2.5–3 m 要求内）。
    """
    ifov_rad = pixel_size_m / focal_length_m
    return altitude_km * 1000.0 * ifov_rad


@analysis(
    desc="クロストラック スワス幅 [km]（telescope/image_sensors/orbital 参照）",
    imports=["orbital"],
)
def swath_width_km(
    image_sensors: Annotated[vq.Table, vq.Ref("$.image_sensors")],
    pixel_size_m: Annotated[float, vq.Ref("$.telescope.spec.pixel_size_m")],
    focal_length_m: Annotated[float, vq.Ref("$.telescope.spec.focal_length_m")],
    altitude_km: Annotated[float, vq.Ref("$.orbitalparams.altitude_km", scope="orbital")],
) -> float:
    """クロストラック方向のスワス幅 [km] を返す。

    FoV = cross_track_pixels × IFOV として toolbox.swath_width_m で計算。
    画素数は image_sensors、光学は telescope、高度は orbital を参照。
    ONGLAISAT: 8192 × 6.897e-6 rad → FoV ≈ 0.0565 rad → 約 23.2 km。
    """
    sensor = image_sensors["rsi_tdi"]
    ifov_rad = pixel_size_m / focal_length_m
    fov_rad = float(sensor.spec.cross_track_pixels) * ifov_rad
    return float(swath_width_m(altitude_km * 1000.0, fov_rad)) / 1000.0


@analysis(desc="TDI 積分段数による SNR 向上倍率（= √tdi_stages, image_sensors 参照）")
def tdi_snr_factor(
    image_sensors: Annotated[vq.Table, vq.Ref("$.image_sensors")],
) -> float:
    """TDI の SNR 向上倍率 [−] を返す（ショットノイズ律速近似 SNR ∝ √N）。

    TDI 段数は image_sensors を参照（ハードコードしない）。
    ONGLAISAT: stage_mode = 8 → SNR 向上 ≈ 2.828×（単段比）。
    """
    import math

    return math.sqrt(image_sensors["rsi_tdi"].spec.tdi_stages)


@analysis(desc="1 ミッションあたりダウンリンク画像データ量 [MB]（image_sensors/processor 参照）")
def scene_data_volume_mbyte(
    image_sensors: Annotated[vq.Table, vq.Ref("$.image_sensors")],
    image_processors: Annotated[vq.Table, vq.Ref("$.image_processors")],
) -> float:
    """1 ミッション（全フレーム）あたりの圧縮後（DL）画像データ量 [MB] を返す。

    画素数・ライン数・フレーム数・量子化ビットは image_sensors、圧縮率は
    image_processors.design を参照（ハードコードしない）。X バンド DL 帯域との比較用。
    生データ: 8192 × 378 × 10 bit × 10 frames ÷ 8e6 ≈ 38.8 MB（圧縮率 1 相当）。
    """
    sensor = image_sensors["rsi_tdi"]
    processor = image_processors["mobc_imaging"]
    return float(
        observation_data_volume_mbyte(
            horizontal_pixels=float(sensor.spec.cross_track_pixels),
            vertical_pixels=float(sensor.spec.lines_per_frame),
            bits_per_pixel=float(sensor.design.bits_per_pixel),
            frame_count=float(sensor.spec.frames_per_mission),
            compression_ratio=processor.design.compression_ratio,
        )
    )
