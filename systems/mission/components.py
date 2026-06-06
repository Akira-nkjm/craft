"""Mission system components — ONGLAISAT ミッションペイロード。

注意: `from __future__ import annotations` は書かない（veriq の inspect.signature を壊す）。

ONGLAISAT 主ミッション: 高分解能光学地球観測（GSD 2.5–3 m @410 km、TDI）。
ペイロード構成:
  - Korsch 光学系（TASA 製 Korsch オフアクシス望遠鏡）— 受動、焦点距離 725 mm
  - TDI イメージセンサ（TSRI 製 CMOS-TDI ライン）— 撮像時 ON（MISSION_1）
  - Mission IF ボード（ISSL 製 MIF、Xilinx Zynq-7020）— 撮像時 ON（MISSION_IF）
  - 画像処理（MOBC 上のオンボード圧縮）— 撮像時 ON（MISSION_2）

出典:
  - S2E telescope.ini / rsi.ini / mission_if.ini（S2E シミュレータ設定）
  - 宇科連2023（Tsutsui ほか、ISSL 宇宙科学技術連合講演会論文）
  - PCDU チャネル情報（Power Overview §5）
  - 質量シート mass_inertia_breakdown.csv「4.Mission」
"""

from craft.schema import (
    Component,
    MultiInstance,
    Placeable,
    PowerConsuming,
    TemperatureSensitive,
    fld,
)


class Telescope(Component, Placeable):
    """Korsch オフアクシス反射望遠鏡（光学系）。

    ONGLAISAT: TASA 製 Korsch 型オフアクシス 3 枚鏡系。
    受動系（電力消費なし）。焦点距離・画素ピッチから GSD・スワス幅の計算基準となる。
    視線方向（LoS）はコンポーネント +X 軸（telescope.ini quaternion_b2c から）。
    排除角は太陽・地球・月 各 60°（telescope.ini *_exclusion_angle_deg）。

    Source: [確定値] S2E telescope.ini（focal_length_m, pixel_size_m, *_exclusion_angle_deg）
            [宇科連2023] Tsutsui ほか / [[Optics (Korsch)]]
    """

    # --- 必須フィールド（デフォルトなし）---
    focal_length_m: float = fld(ge=0, unit="m", desc="焦点距離 [m] [確定値: S2E telescope.ini]")
    pixel_size_m: float = fld(
        ge=0, unit="m", desc="焦点面画素ピッチ [m] [確定値: S2E telescope.ini]"
    )
    # --- オプションフィールド（デフォルトあり）---
    aperture_diameter_m: float = fld(
        ge=0, unit="m", default=0.0, desc="開口径 [m] [推測: f/5 仮定 Ø145 mm]"
    )
    f_number: float = fld(ge=0, default=0.0, desc="F 値 [推測: f/5]")
    ifov_rad: float = fld(
        ge=0,
        unit="rad",
        default=0.0,
        desc="1 画素瞬時視野角 IFOV [rad]（= pixel_size_m / focal_length_m）[確定値: S2E]",
    )
    sun_exclusion_angle_deg: float = fld(
        ge=0,
        unit="deg",
        default=60.0,
        desc="太陽排除角 [deg] [確定値: S2E telescope.ini sun_exclusion_angle_deg=60]",
    )
    earth_exclusion_angle_deg: float = fld(
        ge=0,
        unit="deg",
        default=60.0,
        desc="地球排除角 [deg] [確定値: S2E telescope.ini earth_exclusion_angle_deg=60]",
    )
    moon_exclusion_angle_deg: float = fld(
        ge=0,
        unit="deg",
        default=60.0,
        desc="月排除角 [deg] [確定値: S2E telescope.ini moon_exclusion_angle_deg=60]",
    )
    telescope_type: str = fld(default="Korsch off-axis", desc="望遠鏡形式")
    manufacturer: str = fld(default="TASA", desc="製造機関（台湾宇宙機関）")


class ImageSensor(Component, MultiInstance, PowerConsuming, TemperatureSensitive, Placeable):
    """CMOS-TDI ラインセンサ（焦点面検出器）。

    ONGLAISAT: TSRI（台湾半導体研究所）製 CMOS-TDI ラインセンサ。
    X 方向（32 画素）= TDI 積分段方向、Y 方向（8192 画素）= クロストラック方向。
    有効 TDI 段数 8 段（`stage_mode = 8`）。
    PCDU チャネル MISSION_1（11.51 W）が供給先（推測: RSI/EU 系含む）。
    撮像時（imaging モード）のみ ON。

    Source: [確定値] S2E telescope.ini
            （x/y_number_of_pixel=32/8192, pixel_size_m=5e-6, stage_mode=8）
            [確定値] TDI-analysis（ラインレート=0.000423 s, lines_per_frame=378）
            [確定値] PCDU MISSION_1 = 11.51 W（Power Overview §5）
            [宇科連2023] Tsutsui ほか
    """

    # --- センサ配列 ---
    x_pixels: int = fld(ge=1, desc="X 方向（TDI 段方向）画素数 [確定値: S2E x_number_of_pixel=32]")
    y_pixels: int = fld(
        ge=1, desc="Y 方向（クロストラック方向）画素数 [確定値: S2E y_number_of_pixel=8192]"
    )
    pixel_size_m: float = fld(
        ge=0, unit="m", desc="画素ピッチ [m] [確定値: S2E pixel_size_m=5.0e-6]"
    )
    tdi_stages: int = fld(ge=1, desc="有効 TDI 段数（stage_mode）[確定値: S2E stage_mode=8]")
    tdi_max_stages: int = fld(
        ge=1, default=32, desc="最大 TDI 段数（物理配列 X 方向画素数）[確定値: S2E]"
    )

    # --- 撮像パラメータ ---
    line_rate_s: float = fld(
        ge=0,
        unit="s",
        default=0.0,
        desc="TDI ラインレート [s/line] [確定値: TDI-analysis 最適化値 0.000423 s]",
    )
    lines_per_frame: int = fld(
        ge=0, default=0, desc="1 フレームあたりライン数 [確定値: TDI-analysis 378 lines]"
    )
    frames_per_mission: int = fld(
        ge=0,
        default=0,
        desc="1 ミッションあたりフレーム数 [確定値: S2E number_of_frames_per_mission=10]",
    )

    # --- センサ種別 ---
    sensor_type: str = fld(default="CMOS TDI", desc="センサ形式")
    manufacturer: str = fld(default="TSRI", desc="製造機関（台湾半導体研究所）")

    class Design:
        bits_per_pixel: int = fld(
            ge=1, default=10, desc="量子化ビット深度 [bit/px] [推測: 10–12 bit 典型]"
        )


class MissionInterface(Component, MultiInstance, PowerConsuming, Placeable):
    """Mission IF ボード（ミッション電装インタフェース）。

    ONGLAISAT: ISSL 新規開発、SPHERE-1 EYE と共通設計。SoC = Xilinx Zynq-7020
    （ARM Cortex-A9 + FPGA）。RS422 で MOBC（port 3）・RSI（port 4）と接続。
    役割: ① 電源/通信ラインの中継、② 撮像データの CCSDS パケット変換 → XTx 送出。
    XTx 不調時は STx（S 帯）経由でバックアップ DL。
    PCDU チャネル MISSION_IF（2.10 W）が供給先。
    撮像時（imaging モード）のみ ON。

    Source: [確定値] S2E mission_if.ini（port_id=3, PORT_CH_RS422_MIS_IF）
            [確定値] 質量 77.05 g（宇科連2023 Tsutsui ほか）
            [確定値] PCDU MISSION_IF = 2.10 W（Power Overview §5）
            [宇科連2023] ISSL 宇宙科学技術連合講演会論文
    """

    soc: str = fld(
        default="Xilinx Zynq-7020", desc="搭載 SoC（ARM Cortex-A9 + FPGA）[確定値: 宇科連2023]"
    )
    interface_type: str = fld(
        default="RS422", desc="通信インタフェース [確定値: S2E mission_if.ini]"
    )
    ccsds_packet_protocol: str = fld(
        default="CCSDS Space Packet Protocol Blue Book 2020",
        desc="CCSDS パケット変換規格 [確定値: 宇科連2023]",
    )
    manufacturer: str = fld(default="ISSL", desc="製造機関（東京大学 中須賀・船瀬研究室）")


class ImageProcessor(Component, MultiInstance, PowerConsuming, Placeable):
    """オンボード画像処理・圧縮（MOBC 上のソフトウェア処理機能）。

    ONGLAISAT: MOBC（ミッション系オンボード計算機）が担当。TDI 生ライン画像を
    取込・前処理（暗電流補正/欠陥画素/ライン整列）・圧縮・蓄積し、XTx へ送出。
    PCDU チャネル MISSION_2（8.14 W）が供給先（推測: FPA/センサ系追加分）。
    圧縮方式は非公開（推測: CCSDS-IDC / JPEG2000 系）。
    撮像時（imaging モード）のみ ON。

    Source: [確定値] S2E telescope.ini（number_of_frames_per_mission=10）
            [確定値] PCDU MISSION_2 = 8.14 W（Power Overview §5）
            [宇科連2023] オンボード圧縮実証の記述
            [推測] 圧縮方式・圧縮率は非公開
    """

    compression_algorithm: str = fld(
        default="CCSDS-IDC/JPEG2000 (推測)",
        desc="画像圧縮アルゴリズム（非公開 → 推測フラグ）",
    )
    frames_per_mission: int = fld(
        ge=0,
        default=10,
        desc="1 ミッションあたりフレーム数 [確定値: S2E number_of_frames_per_mission=10]",
    )
    processing_host: str = fld(default="MOBC", desc="処理実行ホスト [確定値: 宇科連2023]")

    class Design:
        compression_ratio: float = fld(
            ge=1.0, default=4.0, desc="圧縮率 [推測: 数分の1〜十数分の1。実機仕様は非公開]"
        )
