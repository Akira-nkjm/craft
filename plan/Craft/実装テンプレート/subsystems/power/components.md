---
tags: [project, dev, satellite, template, code]
mirror: subsystems/power/components.py
---

# subsystems/power/components.py

> 親: [[実装テンプレート/README|実装テンプレート]]

電力サブシステムの component 定義。
**`@component` decorator は無い**。全部 `Component` base class + trait 多重継承。

---

## ファイル全体

```python
"""Power subsystem components."""

# 注意: from __future__ import annotations は書かない（veriq の inspect.signature を壊す）

from craft.schema import Component, fld
from craft.schema.traits import (
    PowerConsuming,
    TemperatureSensitive,
    MultiInstance,
)


class Battery(Component, MultiInstance, TemperatureSensitive):
    """二次電池。eclipse 中の電力供給を担う。"""

    capacity_wh: float = fld(ge=0, unit="Wh", desc="Battery capacity")
    nominal_voltage_v: float = fld(ge=0, unit="V", default=0.0)
    manufacturer: str = fld(default="", desc="Manufacturer")

    class Design:
        depth_of_discharge: float = fld(ge=0, le=1, desc="設計時 DoD")

    class Requirements:
        depth_of_discharge_max: float = fld(default=0.8, gt=0, le=1, desc="要求 DoD 上限")


class SolarPanel(Component, MultiInstance, TemperatureSensitive):
    """太陽電池パドル。発電 component は SAP しか無いので trait 抽象化せず直接 field を持つ。"""

    area_m2: float = fld(ge=0, unit="m^2", desc="Panel area")
    efficiency: float = fld(ge=0, le=1, default=0.28, desc="セル効率")
    default_power_generation_per_unit_w: float = fld(
        ge=0, unit="W", desc="想定発電量 (BOL/EOL 別途 design で扱う)"
    )

    class Design:
        cell_count: int = fld(ge=1)
        string_count: int = fld(ge=1)


class PDM(Component, MultiInstance, PowerConsuming):
    """Power Distribution Module。PowerConsuming → 自動的に power_modes 付き。"""

    rated_current_a: float = fld(ge=0, unit="A")

    class Design:
        efficiency: float = fld(ge=0, le=1, default=0.95)
```

---

## 解説

### `class Battery(Component, MultiInstance, TemperatureSensitive):`

| 部分 | 意味 |
|---|---|
| `Component` | 必須の基底クラス。 **必ず最左** に置く（MRO の解決順序のため） |
| `TemperatureSensitive` | trait。動作温度範囲のフィールドを自動付与 |
| `(他の trait)` | 多重継承で任意個重ねる |

→ **decorator が消えた分、宣言が短く・型に厳しくなる**。`pyrefly` / IDE は `Battery` の全 field を `Component.__init_subclass__` + `dataclass_transform` 経由で正しく型認識する。

### subsystem は自動推論される

ファイルパスが `subsystems/power/components.py` なので、`Component.__init_subclass__` がこれを検出し `subsystem="power"` を自動セット。

明示したい場合は:
```python
class Battery(Component, TemperatureSensitive, subsystem="power_alt"):
    ...
```
PEP 487 のキーワード引数で渡す。

### trait の効果

| trait | 自動付与される field |
|---|---|
| `PowerConsuming` | Spec に `default_power_consumption_per_unit_w` + Design に `power_modes: dict[OperationMode, bool]` |
| `TemperatureSensitive` | Spec に `operating_temperature_min_c`, `operating_temperature_max_c` |
| `SpecOnly` | Design 自動生成をスキップ（datasheet 的 component） |

詳細は [[実装テンプレート/_internals/trait一覧]]。

### `class Design:` / `class Requirements:`

省略可能。書かない場合は空のものが自動生成される。 **空でも構造的には作られる**（TOML では `[batteries.main.design]` テーブルが空で許される）。

### 自動生成される名前（gen_stubs 経由で `.pyi` に出る）

```
class Battery(Component, MultiInstance, TemperatureSensitive):
  ↓
Battery.Spec           ← Spec model（capacity_wh / nominal_voltage_v 等）
Battery.Design         ← Design model
Battery.Requirements   ← Requirements model
Battery.Entry          ← spec + design + requirements + meta をまとめた envelope
```

→ アクセスは `Battery.Spec` / `Battery.Entry` のように **属性経由**。これにより gen_stubs に頼らなくても `dataclass_transform` 由来で型補完が大体効く。完全補完用に stub も生成可能（CI gate）。

---

## やってはいけないこと

- ❌ `Component` を最左に置かない `class Battery(TemperatureSensitive, Component):` （MRO が意図と違う）
- ❌ `from __future__ import annotations`
- ❌ `Spec` / `Design` / `Requirements` 以外の inner class
- ❌ `_` で始まるプライベート field（TOML キーにマップできない）
- ❌ `Component` を継承せずに trait だけ継承 `class Battery(TemperatureSensitive):` （registry 登録されない）
