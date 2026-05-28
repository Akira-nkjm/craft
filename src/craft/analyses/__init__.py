"""Cross-subsystem aggregation helpers for analyses.

`systems/<sys>/analyses.py` から `from craft.analyses import ...` で使う。

- `aggregation` 系（`total_mass_kg`, `power_per_mode`, ...）— vq.Table / Singleton を
  統一的に走査して値を合算する低レベルヘルパ。@analysis 関数の body で使う。
- `auto_inject_refs` — `@analysis` の下に重ねる decorator。registry から component を
  自動列挙して `Annotated[vq.Table, vq.Ref(...)]` 引数を一括注入する。
  30+ 個の引数を手書きしなくて済む。
"""

from craft.analyses.aggregation import (
    iter_instances,
    power_for_mode,
    power_per_mode,
    total_mass_kg,
    total_quantity,
)
from craft.analyses.builder import (
    all_component_refs,
    auto_inject_refs,
)

__all__ = [
    "all_component_refs",
    "auto_inject_refs",
    "iter_instances",
    "power_for_mode",
    "power_per_mode",
    "total_mass_kg",
    "total_quantity",
]
