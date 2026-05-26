---
tags: [project, dev, satellite, template, code]
mirror: subsystems/thermal/components.py
---

# subsystems/thermal/components.py

> 親: [[実装テンプレート/README|実装テンプレート]]

熱サブシステム。**SpecOnly trait** (Design 自動生成スキップ) の例を含む。

---

## ファイル全体

```python
"""Thermal subsystem components."""

from craft.schema import Component, fld
from craft.schema import Component, MultiInstance, fld
from craft.schema.traits import (
    PowerConsuming,
    HasPowerMode,
    SpecOnly,
)


class Heater(Component, MultiInstance, PowerConsuming, HasPowerMode):
    """搭載ヒータ。配置複数で MultiInstance。OperationMode ごとに on/off を切替。"""

    rated_power_w: float = fld(ge=0, unit="W", desc="定格電力")
    target_temperature_c: float = fld(unit="degC", desc="目標温度")

    class Design:
        hysteresis_c: float = fld(ge=0, default=2.0, unit="degC", desc="ヒステリシス幅")


class PanelSurface(Component, MultiInstance, SpecOnly):
    """パネル表面の熱光学物性。material library として複数種、Design なし。"""

    emissivity: float = fld(ge=0, le=1, desc="放射率")
    absorptivity: float = fld(ge=0, le=1, desc="太陽光吸収率")
    surface_treatment: str = fld(default="", desc="表面処理（白塗装/MLI 等）")
```

---

## 解説

### `SpecOnly` trait の意味

```python
class PanelSurface(Component, SpecOnly):
    emissivity: float = fld(...)
    # class Design: を書かない
```

`SpecOnly` trait があると `Component.__init_subclass__` が **Design 自動生成をスキップ**。
登録される model は `Spec` と `Entry` のみ（`Design` / `Requirements` は無し）。

### SpecOnly なしで Design 省略との違い

```python
# (A) SpecOnly 明示
class PanelSurface(Component, SpecOnly):
    emissivity: float = fld(...)
# → Spec のみ。Design 概念がそもそも無い

# (B) SpecOnly なし、Design 省略
class PanelSurface(Component):
    emissivity: float = fld(...)
# → Spec + 空 Design が作られる。TOML の [.design] テーブルは空で書く
```

| 観点 | (A) SpecOnly | (B) Design 省略 |
|---|---|---|
| 意図の明示 | ✅ 「設計判断なし」を明言 | ⚠️ うっかり書き忘れに見える |
| TOML の `[.design]` | ❌ 不要 | ✅ 空テーブル必要 |
| 推奨 | ✅ 意図的な場合はこちら | ❌ 通常は使わない |

→ **意図的に Design を持たない** なら `SpecOnly` trait を明示推奨。

### TOML の見え方

```toml
# Heater
[heaters.main_heater]
[heaters.main_heater.spec]
rated_power_w = 5.0
target_temperature_c = -10
default_power_consumption_per_unit_w = 5.0   # PowerConsuming

[heaters.main_heater.design]
hysteresis_c = 2.0

[heaters.main_heater.design.power_modes]     # HasPowerMode
safe = true
nominal = true


# PanelSurface (SpecOnly)
[panel_surfaces.white_paint]
[panel_surfaces.white_paint.spec]
emissivity = 0.9
absorptivity = 0.2
surface_treatment = "白塗装"
# ↑ [.design] テーブル無し！SpecOnly trait の効果
```
