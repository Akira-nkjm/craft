"""Mission-level configurations。"""

from enum import StrEnum

from craft.schema import Config, MultiInstance, fld


class OperationMode(StrEnum):
    """衛星の運用モード。値はここで自由に追加・変更できる。

    Source: SEIRIOS 子衛星 電源モード検討 (shared drive: SEIRIOS)。
    フェーズ別に 子衛星単独運用 / 合体時特殊運用 / FF運用 を区切る。
    """

    # --- 子衛星単独運用 ---
    SAFE = "safe"  # セーフモード（姿勢制御無し）
    SUN_ACQUISITION = "sun_acquisition"  # 太陽捕捉
    COARSE_3AXIS = "coarse_3axis"  # 粗三軸 (RW)
    FINE_3AXIS = "fine_3axis"  # 精三軸 (STT+RW)
    PROPULSION = "propulsion"  # 推進系運用

    # --- 合体時 (mated) ---
    MATED_CHECK = "mated_check"  # 子衛星動作確認
    MATED_CALIBRATION = "mated_calibration"  # キャリブレーション
    MATED_ACTUATOR = "mated_actuator"  # アクチュエータ動作

    # --- FF 運用 (Formation Flying) ---
    COARSE_FF = "coarse_ff"  # 粗FF（CDGNSS のみ）
    FINE_FF = "fine_ff"  # 精FF（光学・レーザー）


class MissionProfile(Config):
    """ミッションプロファイル全体。"""

    duration_years: float = fld(ge=0, unit="year", desc="ミッション期間")
    target_altitude_km: float = fld(ge=0, unit="km", desc="目標高度")
    primary_payload: str = fld(desc="主ペイロード種別")
    contact_frequency_per_day: int = fld(ge=0, desc="1 日あたりの地上局可視回数")
    launch_window_start: str = fld(desc="打ち上げ窓開始 (ISO8601)")


class OrbitalParameters(Config):
    """軌道要素（古典 6 元素）。"""

    semi_major_axis_km: float = fld(ge=0, unit="km")
    eccentricity: float = fld(ge=0, lt=1)
    inclination_deg: float = fld(ge=0, le=180, unit="deg")
    raan_deg: float = fld(ge=0, lt=360, unit="deg", desc="昇交点赤経")
    arg_periapsis_deg: float = fld(ge=0, lt=360, unit="deg", desc="近点引数")
    mean_anomaly_deg: float = fld(ge=0, lt=360, unit="deg", desc="平均近点角")
    epoch_utc: str = fld(desc="元期 (ISO8601 UTC)")


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
