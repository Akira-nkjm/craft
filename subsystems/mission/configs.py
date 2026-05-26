"""Mission-level configurations。"""

from schema import Config, fld


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
