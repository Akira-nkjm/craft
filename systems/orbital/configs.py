"""Orbital system configs."""

from craft.schema import Config, fld


class OrbitalParams(Config):
    """軌道パラメータ。"""

    altitude_km: float = fld(ge=0, unit="km", desc="軌道高度")
    period_min: float = fld(ge=0, unit="min", desc="軌道周期")
    eclipse_duration_s: float = fld(ge=0, unit="s", desc="食時間")
