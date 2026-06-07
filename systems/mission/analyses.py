"""Mission-level analyses（衛星全体ビュー + ペイロード解析）。

`@auto_inject_refs` が registry から全 component を列挙して
`Annotated[vq.Table, vq.Ref(...)]` 引数を一括注入する。元関数は
`*tables` で受け取り、body は 1 行で書ける。

ペイロード解析（toolbox.payload）:
  - pixel_gsd_m     : 画素 IFOV から GSD [m] を計算（toolbox.payload.imaging）
  - swath_width_km  : クロストラック スワス幅 [km]（toolbox.payload.imaging）
  - tdi_snr_factor  : TDI 積分段数による SNR 向上倍率（toolbox.payload.detector）
  - scene_data_volume_mbyte : 1 ミッションあたり画像データ量 [MB]（toolbox.payload.data）
"""

from toolbox.payload.data import observation_data_volume_mbyte
from toolbox.payload.imaging import swath_width_m

from craft.analyses import auto_inject_refs, total_mass_kg, total_quantity
from craft.schema import analysis


@analysis(desc="衛星全体の総質量 [kg]（コンポ + 構造体 + 推進剤）= wet mass 相当")
@auto_inject_refs()
def total_bus_mass_kg(*tables) -> float:
    """全 instance の spec.mass_kg × design.quantity を合算 [kg]。"""
    return total_mass_kg(*tables)


@analysis(desc="衛星全体の搭載コンポ個数（quantity 合計、debug 用）")
@auto_inject_refs()
def total_component_count(*tables) -> int:
    """全テーブルの quantity 合計。"""
    return total_quantity(*tables)


# ─── ペイロード光学・撮像解析（ad-hoc、veriq 非登録）─────────────────────────


@analysis(
    system=None,
    desc="画素 IFOV から GSD [m] を計算（H × pixel_size / focal_length）",
    cache=True,
)
def pixel_gsd_m(
    altitude_m: float = 410_000.0,
    pixel_size_m: float = 5.0e-6,
    focal_length_m: float = 0.725,
) -> float:
    """画素 IFOV（= pixel_size / focal_length）から地表 GSD [m] を返す。

    ONGLAISAT 確定値: GSD = 410,000 × 5e-6 / 0.725 ≈ 2.828 m（2.5–3 m 要求内）。
    Source: [確定値] S2E telescope.ini（pixel_size_m=5e-6, focal_length_m=0.725）
    """
    ifov_rad = pixel_size_m / focal_length_m
    return altitude_m * ifov_rad


@analysis(
    system=None,
    desc="クロストラック スワス幅 [km]（toolbox.payload.imaging.swath_width_m を利用）",
    cache=True,
)
def swath_width_km(
    altitude_m: float = 410_000.0,
    pixel_size_m: float = 5.0e-6,
    focal_length_m: float = 0.725,
    y_pixels: int = 8192,
) -> float:
    """クロストラック方向のスワス幅 [km] を返す。

    FoV = y_pixels × IFOV（rad）として toolbox.swath_width_m で計算。
    ONGLAISAT 確定値: 8192 × 6.897e-6 rad → FoV ≈ 0.05651 rad → 約 23.2 km。
    Source: [確定値] S2E telescope.ini
            （y_number_of_pixel=8192, pixel_size_m=5e-6, focal_length_m=0.725）
    """
    ifov_rad = pixel_size_m / focal_length_m
    fov_rad = float(y_pixels) * ifov_rad
    return float(swath_width_m(altitude_m, fov_rad)) / 1000.0


@analysis(
    system=None,
    desc="TDI 積分段数による SNR 向上倍率（= √tdi_stages 、ショットノイズ律速近似）",
    cache=True,
)
def tdi_snr_factor(
    tdi_stages: int = 8,
) -> float:
    """TDI の SNR 向上倍率 [−] を返す。

    ショットノイズ律速近似: SNR ∝ √N（N = TDI 段数）。
    ONGLAISAT: stage_mode = 8 → SNR 向上 ≈ 2.828×（単段比）。
    Source: [確定値] S2E telescope.ini stage_mode=8 / TDI-analysis
    """
    import math

    return math.sqrt(tdi_stages)


@analysis(
    system=None,
    desc="1 ミッションあたり画像データ量 [MB]（toolbox.payload.data）",
    cache=True,
)
def scene_data_volume_mbyte(
    y_pixels: int = 8192,
    lines_per_frame: int = 378,
    bits_per_pixel: int = 10,
    frames_per_mission: int = 10,
    compression_ratio: float = 1.0,
) -> float:
    """1 ミッション（10 フレーム）あたり画像データ量 [MB] を返す。

    生データ（圧縮なし）: 8192 × 378 × 10 bit × 10 frames ÷ 8e6 ≈ 38.8 MB / mission。
    X バンド DL 帯域との比較に使う。compression_ratio > 1 で圧縮後データ量を返す。
    Source: [確定値] TDI-analysis lines_per_frame=378, S2E number_of_frames=10
            [確定値] S2E y_number_of_pixel=8192
            [推測] bits_per_pixel=10
    """
    return float(
        observation_data_volume_mbyte(
            horizontal_pixels=float(y_pixels),
            vertical_pixels=float(lines_per_frame),
            bits_per_pixel=float(bits_per_pixel),
            frame_count=float(frames_per_mission),
            compression_ratio=compression_ratio,
        )
    )
