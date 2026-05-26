---
tags: [project, dev, satellite, template, code]
mirror: schema/subsystems/power.py
---

# schema/subsystems/power.py

> 親: [[実装テンプレート/README|実装テンプレート]]

電力サブシステムの component 定義。
**`@component` decorator だけを使う**、Pydantic は意識しなくて良い。

---

## ファイル全体

```python
"""Power subsystem components."""

from craft.schema import component, fld


@component(subsystem="power", mixin="temperature")
class Battery:
    """二次電池。eclipse 中の電力供給を担う。"""

    capacity_wh: float = fld(ge=0, unit="Wh", desc="Battery capacity")
    nominal_voltage_v: float = fld(ge=0, unit="V", default=0.0)
    manufacturer: str = fld(default="", desc="Manufacturer")

    class Design:
        depth_of_discharge: float = fld(ge=0, le=1, desc="設計時 DoD")

    class Requirements:
        depth_of_discharge_max: float = fld(default=0.8, gt=0, le=1, desc="要求 DoD 上限")


@component(subsystem="power", base="power_spec", mixin="temperature")
class SolarPanel:
    """太陽電池パドル。"""

    area_m2: float = fld(ge=0, unit="m^2", desc="Panel area")
    efficiency: float = fld(ge=0, le=1, default=0.28, desc="セル効率")

    class Design:
        cell_count: int = fld(ge=1)
        string_count: int = fld(ge=1)


@component(subsystem="power", has_power_mode=True)
class PDM:
    """Power Distribution Module。OperationMode ごとに電力配分を持つ。"""

    rated_current_a: float = fld(ge=0, unit="A")

    class Design:
        # has_power_mode=True → BaseDesignWithPowerMode が自動継承され、
        # 各 OperationMode の on/off / 配分が記述可能になる
        efficiency: float = fld(ge=0, le=1, default=0.95)
```

---

## 解説

### `@component(subsystem=..., mixin=..., base=..., has_power_mode=..., plural=...)`

- `subsystem=` — 必須。所属 subsystem 名
- `mixin="temperature"` — 動作温度範囲のフィールドを spec に追加
- `base="power_spec"` — spec 基底を `BasePowerSpec`（`default_power_consumption_per_unit_w` を持つ）に切替
- `has_power_mode=True` — Design に `OperationMode` 別の on/off を持たせる
- `plural=` — TOML テーブル名を上書き（例: `plural="sband_antennas"`）。デフォルトは英語複数形化

### `fld(...)` の引数

- `ge / le / gt / lt` — 数値制約
- `default=` — デフォルト値
- `unit=` — 単位、JSON Schema / Swagger / 自動 doc に伝達
- `desc=` — 説明文
- `group= / order=` — UI hint（Web UI 時代に効く、今は無害）

### inner class

- `class Design:` — 設計値（手で書く設計判断）
- `class Requirements:` — 要求仕様（満たすべき制約）

両方とも省略可能。`Design` が無い component は datasheet 的存在（後述）。

### 自動生成される名前

```
@component class Battery:
  ↓
BatterySpec          ← Spec の fields
BatteryDesign        ← Design の fields
BatteryRequirements  ← Requirements の fields
BatteryEntry         ← spec + design + requirements + meta をまとめた envelope
```

これらは [[gen_stubs]] によって `.pyi` に書き出され、IDE / pyrefly から見える。

---

## 「やってはいけないこと」

- ❌ `from __future__ import annotations` — veriq が壊れる
- ❌ Pydantic を直接 import して BaseModel を継承 — `@component` の責務を侵す
- ❌ `Spec` / `Design` 以外の inner class — 命名規約から外れる
- ❌ プライベートフィールド `_x` — TOML キーにマッピングできない
