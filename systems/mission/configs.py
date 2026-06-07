"""Mission-level configurations。"""

from enum import StrEnum

from craft.schema import Config, MultiInstance, fld


class OperationMode(StrEnum):
    """衛星の運用モード。値はここで自由に追加・変更できる。

    Source: ONGLAISAT C2A フライトソフト Mode Manager（権威・一次情報）。
      - AOBC: `MM_START_TRANSITION` 引数定義
        `Start=0; Initial=1; Bdot=2; SunPoint=3; R3ax-MTQ=4; R3ax-RW=5; F3ax=6`
        （99_Sources/raw/tlm_cmd_db/db/cmddb, *.ops の遷移コメント）
      - MOBC: INITIAL → NOMINAL、撮像シーケンスでミッション遷移
    姿勢制御チェーン（C2A）に、撮像 / X帯DL の活動オーバーレイ
    （Power Overview §5）を加えた 8 モード。
    """

    # --- 姿勢制御チェーン (C2A AOBC Mode Manager) ---
    INITIAL = "initial"  # 起動直後（最小構成、CDH のみ）
    BDOT = "bdot"  # デタンブル（MTQ + 磁気センサ）
    ROUGH_SUN_POINTING = "rough_sun_pointing"  # 太陽捕捉（太陽センサ + MTQ）
    ROUGH_THREE_AXIS_MTQ = "rough_three_axis_mtq"  # 粗三軸（MTQ 制御）
    ROUGH_THREE_AXIS_RW = "rough_three_axis_rw"  # 粗三軸（RW 制御）
    FINE_THREE_AXIS = "fine_three_axis"  # 精三軸（STT+RW、NOMINAL/撮像待機姿勢）

    # --- 活動オーバーレイ (MOBC ミッション / Power Overview §5) ---
    IMAGING = "imaging"  # 撮像実行（fine_three_axis + MISSION_IF/1/2）
    XBAND_DOWNLINK = "xband_downlink"  # X帯ダウンリンク（fine + XTx）


class MissionProfile(Config):
    """ミッションプロファイル全体。"""

    duration_years: float = fld(ge=0, unit="year", desc="ミッション期間")
    target_altitude_km: float = fld(ge=0, unit="km", desc="目標高度")
    primary_payload: str = fld(desc="主ペイロード種別")
    contact_frequency_per_day: int = fld(ge=0, desc="1 日あたりの地上局可視回数")
    launch_window_start: str = fld(desc="打ち上げ窓開始 (ISO8601)")
    flight_mass_kg: float = fld(
        ge=0, default=0.0, unit="kg", desc="フライト確定全機質量（質量バジェット基準値）"
    )


class OrbitalParameters(Config):
    """軌道要素（古典 6 元素）。"""

    semi_major_axis_km: float = fld(ge=0, unit="km")
    eccentricity: float = fld(ge=0, lt=1)
    inclination_deg: float = fld(ge=0, le=180, unit="deg")
    raan_deg: float = fld(ge=0, lt=360, unit="deg", desc="昇交点赤経")
    arg_periapsis_deg: float = fld(ge=0, lt=360, unit="deg", desc="近点引数")
    mean_anomaly_deg: float = fld(ge=0, lt=360, unit="deg", desc="平均近点角")
    epoch_utc: str = fld(desc="元期 (ISO8601 UTC)")


class MassProperties(Config):
    """全機（フライト）の慣性特性。AOCS 外乱・構体解析の共通参照源。

    値は [確定値] S2E satellite_structure.ini [KINEMATIC_PARAMETERS]（衛星座標系・対角）。
    flight_mass_kg は MissionProfile 側に置く（質量バジェット基準）。
    """

    ixx_kg_m2: float = fld(ge=0, unit="kg*m^2", desc="慣性モーメント Ixx")
    iyy_kg_m2: float = fld(ge=0, unit="kg*m^2", desc="慣性モーメント Iyy（最大主慣性軸）")
    izz_kg_m2: float = fld(ge=0, unit="kg*m^2", desc="慣性モーメント Izz（最小 = 長軸 Z）")


class OperationModeConfig(Config, MultiInstance):
    """運用モードの定義。key = OperationMode の値（同ファイル内 StrEnum と対応）。

    power_modes（PowerConsuming trait）と組み合わせてモード別電力解析に使う。
    """

    description: str = fld(default="", desc="モードの説明")
    max_duration_s: float = fld(
        ge=0, default=0.0, unit="s", desc="最大連続継続時間 [s]、0 = 制限なし"
    )
    is_initial_mode: bool = fld(default=False, desc="起動直後のデフォルトモード")
    allowed_transitions: list[str] = fld(
        default_factory=list, desc="遷移可能なモード名リスト（空 = すべて許可）"
    )
