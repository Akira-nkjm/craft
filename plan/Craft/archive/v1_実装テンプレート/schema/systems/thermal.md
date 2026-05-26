---
tags: [project, dev, satellite, template, code]
mirror: schema/systems/thermal.py
---

# schema/systems/thermal.py

> 親: [[実装テンプレート/README|実装テンプレート]]

熱サブシステム。**Design を持たない** component の例（`PanelSurface`）を含む。

---

## ファイル全体

```python
"""Thermal system components."""

from craft.schema import component, fld


@component(system="thermal", has_power_mode=True)
class Heater:
    """搭載ヒータ。OperationMode ごとに on/off を切替。"""

    rated_power_w: float = fld(ge=0, unit="W", desc="定格電力")
    target_temperature_c: float = fld(unit="degC", desc="目標温度")

    class Design:
        hysteresis_c: float = fld(ge=0, default=2.0, unit="degC", desc="ヒステリシス幅")


@component(system="thermal")
class PanelSurface:
    """パネル表面の熱光学物性。Design なし（datasheet 的）。"""

    emissivity: float = fld(ge=0, le=1, desc="放射率")
    absorptivity: float = fld(ge=0, le=1, desc="太陽光吸収率")
    surface_treatment: str = fld(default="", desc="表面処理（白塗装/MLI 等）")

    # ← class Design は書かない。空 Design として自動生成される
```

---

## 解説

### `Design` を書かない component

`PanelSurface` のように **設計判断要素がほぼ無い** component（≒ datasheet 的）は、`class Design:` を省略可能。
内部では空の Design が自動生成される（`extra="forbid"` のもと未知 field を弾く）。

### TOML の見え方

```toml
[panel_surfaces.white_paint]
[panel_surfaces.white_paint.spec]
emissivity = 0.9
absorptivity = 0.2
surface_treatment = "白塗装"

[panel_surfaces.white_paint.design]
# 空（書かなくて良い）
```

### Heater の `has_power_mode=True`

```toml
[heaters.main_heater]
[heaters.main_heater.spec]
rated_power_w = 5.0
target_temperature_c = -10

[heaters.main_heater.design]
hysteresis_c = 2.0

[heaters.main_heater.design.power_modes]   # ← 自動的にこの構造が許される
safe = true
nominal = true
science = false
```

→ `OperationMode` enum の各値に対する on/off が **「書ける」** ようになる。書かないモードはデフォルト false。
