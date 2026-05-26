---
tags: [project, dev, satellite, template, code]
mirror: systems/power/analyses.py
---

# systems/power/analyses.py

> 親: [[実装テンプレート/README|実装テンプレート]]

電力サブシステムの解析関数。
**関数は decorator のまま**（`@analysis`）。system は親ディレクトリから自動推論。

---

## ファイル全体

```python
"""Power system analyses."""

from typing import Annotated

import veriq as vq

from craft.schema import analysis
from craft.systems.power.components import (
    Battery,
    PDM,
    SolarPanel,
)
from craft.schema.common import OperationMode


# ─── (1) veriq calculation ─────────────────────────────────────

@analysis(desc="OperationMode 別の総消費電力")
def total_power_by_mode(
    pdms: Annotated[vq.Table[str, PDM.Entry], vq.Ref("$.pdms")],
    mode: OperationMode,
) -> float:
    """指定モードでの消費電力合計。"""
    return sum(
        p.spec.default_power_consumption_per_unit_w
        for p in pdms.values()
        if p.design.power_modes.get(mode, False)
    )


# ─── (2) クロス scope 参照あり ──────────────────────────────────

@analysis(
    desc="eclipse 中の必要バッテリーエネルギー",
    imports=["orbital"],
)
def required_battery_energy_wh(
    total_power_safe: Annotated[float, vq.Ref("@total_power_by_mode")],
    eclipse_s: Annotated[float, vq.Ref("@calc_eclipse_duration_s", scope="orbital")],
) -> float:
    return total_power_safe * eclipse_s / 3600.0


# ─── (3) verification: bool を返す ─────────────────────────────

@analysis(
    verify=True,
    desc="全バッテリーが要求 DoD 制約を満たすか",
)
def verify_battery_capacity(
    batteries: Annotated[vq.Table[str, Battery.Entry], vq.Ref("$.batteries")],
    required_energy: Annotated[float, vq.Ref("@required_battery_energy_wh")],
) -> vq.Table[str, bool]:
    return vq.Table({
        name: b.spec.capacity_wh * b.requirements.depth_of_discharge_max >= required_energy
        for name, b in batteries.items()
    })


# ─── (4) ad-hoc 解析: veriq 非連携 ─────────────────────────────

@analysis(
    system=None,                  # ← 明示で「ad-hoc」に
    desc="バッテリー単体の EOL 容量推定",
    cache=True,
)
def battery_eol_capacity(
    spec: Annotated[Battery.Entry, vq.Ref("$.batteries.main")],
    years: float = 5.0,
    cycles_per_day: float = 1.0,
) -> float:
    cycles_total = years * 365 * cycles_per_day
    degradation = min(0.2, 0.0001 * cycles_total)
    return spec.spec.capacity_wh * (1.0 - degradation)
```

---

## 解説

### system の決定ロジック

| 書き方 | 結果 |
|---|---|
| `@analysis(...)` (system 引数なし) | **ディレクトリから自動推論** → `"power"` |
| `@analysis(system="thermal")` | 明示 → `"thermal"` |
| `@analysis(system=None)` | **明示で ad-hoc 化**、veriq 非登録 |

→ 通常は引数なしで OK。ad-hoc にしたい時のみ `system=None` を書く。

### 4 つのパターン

| # | system | verify | 役割 |
|---|---|---|---|
| (1) | 自動推論 (=power) | False | veriq calculation。`@name` で他から参照可 |
| (2) | 自動推論 | False | cross-scope 参照あり (`imports=["orbital"]`) |
| (3) | 自動推論 | True | veriq verification。戻り値は `bool` か `vq.Table[K, bool]` |
| (4) | `None` 明示 | (無視) | ad-hoc。API/CLI 専用 |

### 引数の 3 種類

```python
# (A) 単一 Ref - インスタンス名固定
spec: Annotated[Battery.Entry, vq.Ref("$.batteries.main")]

# (B) Table - 全インスタンス受領（集計向け）
batteries: Annotated[vq.Table[str, Battery.Entry], vq.Ref("$.batteries")]

# (C) 直接パラメータ - API/CLI から渡される
mode: OperationMode
years: float = 5.0
```

### `Battery.Entry` の使い方

`Component` base class が `__init_subclass__` で **属性として `Entry` を生やす**:

```python
Battery.Entry      # → ComponentEntry[Battery.Spec, Battery.Design] 相当
Battery.Spec       # → Battery の Spec model
Battery.Design
Battery.Requirements
```

→ Annotation で参照する時は `Battery.Entry` / `Battery.Spec`。

---

## やってはいけないこと

- ❌ 関数内に副作用（TOML 書き込み、HTTP 呼び出し、I/O）
- ❌ 戻り値に `dict` / `tuple` / `list`（プリミティブ / Pydantic / `vq.Table` のみ）
- ❌ `verify=True` で戻り値が `bool` 系以外
- ❌ `from __future__ import annotations`
- ❌ `@analysis` を component メソッドに貼る（独立関数のみ対象）

---

## テスト

```python
def test_total_power_by_mode():
    from craft.systems.power.analyses import total_power_by_mode
    from craft.systems.power.components import PDM

    pdms = vq.Table({
        "main": PDM.Entry(...),
    })
    result = total_power_by_mode(pdms=pdms, mode=OperationMode.SAFE)
    assert result == pytest.approx(15.0)
```

→ `@analysis` decorator は透過、通常の関数として呼べる。
