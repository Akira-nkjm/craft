"""Cross-subsystem aggregation helpers for analyses.

`systems/<sys>/analyses.py` から `from craft.analyses import ...` で使う。

- `aggregation` 系（`total_mass_kg`, `power_per_mode`, ...）— vq.Table / Singleton を
  統一的に走査して値を合算する低レベルヘルパ。@analysis 関数の body で使う。
"""

from craft.analyses.aggregation import (
    face_of,
    heat_for_mode,
    iter_instances,
    mass_quantity_kg,
    power_for_mode,
    power_per_mode,
    total_mass_kg,
    total_quantity,
)

__all__ = [
    "face_of",
    "heat_for_mode",
    "iter_instances",
    "mass_quantity_kg",
    "power_for_mode",
    "power_per_mode",
    "total_mass_kg",
    "total_quantity",
]
