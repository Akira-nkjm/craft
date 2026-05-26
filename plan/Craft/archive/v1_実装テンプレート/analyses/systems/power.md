---
tags: [project, dev, satellite, template, code]
mirror: analyses/systems/power.py
---

# analyses/systems/power.py

> 親: [[実装テンプレート/README|実装テンプレート]]

電力サブシステムの解析関数。
**3 種の `@analysis`** をすべて含む: ad-hoc / veriq calculation / veriq verification。

---

## ファイル全体

```python
"""Power system analyses."""

from typing import Annotated

import veriq as vq

from craft.analyses import analysis
from craft.schema.systems.power import (
    BatteriesName,
    BatteryEntry,
    PDMsName,
    PDMEntry,
    SolarPanelsName,
    SolarPanelEntry,
)
from craft.schema.common import OperationMode


# ─── (1) veriq calculation: 依存グラフに乗る ────────────────────

@analysis(
    system="power",
    desc="OperationMode 別の総消費電力",
    imports=["orbital"],
)
def total_power_by_mode(
    pdms: Annotated[vq.Table[PDMsName, PDMEntry], vq.Ref("$.pdms")],
    mode: OperationMode,
) -> float:
    """指定モードでの消費電力合計を返す。"""
    return sum(
        p.spec.default_power_consumption_per_unit_w
        for p in pdms.values()
        if p.design.power_modes.get(mode, False)
    )


# ─── (2) veriq calculation: クロス scope 参照あり ──────────────

@analysis(
    system="power",
    desc="eclipse 中の必要バッテリーエネルギー",
    imports=["orbital"],
)
def required_battery_energy_wh(
    total_power_safe: Annotated[float, vq.Ref("@total_power_by_mode")],   # ↑ の結果
    eclipse_s: Annotated[float, vq.Ref("@calc_eclipse_duration_s", scope="orbital")],
) -> float:
    return total_power_safe * eclipse_s / 3600.0


# ─── (3) veriq verification: bool を返す ───────────────────────

@analysis(
    system="power",
    verify=True,
    desc="全バッテリーが要求 DoD 制約を満たすか",
)
def verify_battery_capacity(
    batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")],
    required_energy: Annotated[float, vq.Ref("@required_battery_energy_wh")],
) -> vq.Table[BatteriesName, bool]:
    return vq.Table({
        name: b.spec.capacity_wh * b.requirements.depth_of_discharge_max >= required_energy
        for name, b in batteries.items()
    })


# ─── (4) ad-hoc 解析: veriq に乗らない、API 専用 ───────────────

@analysis(
    desc="バッテリー単体の End-of-Life 容量推定（暫定式）",
    cache=True,
)
def battery_eol_capacity(
    spec: Annotated[BatteryEntry, vq.Ref("$.batteries.main")],   # 単一インスタンス参照
    years: float = 5.0,
    cycles_per_day: float = 1.0,
) -> float:
    cycles_total = years * 365 * cycles_per_day
    degradation = min(0.2, 0.0001 * cycles_total)
    return spec.spec.capacity_wh * (1.0 - degradation)
```

---

## 解説

### 4 つのパターンの違い

| # | `system` | `verify` | 役割 |
|---|---|---|---|
| (1) | `"power"` | False | veriq の calculation。依存グラフに乗り、他 calc から `@total_power_by_mode` で参照可能 |
| (2) | `"power"` | False | 他の calc 結果 + cross-scope を組み合わせる典型 |
| (3) | `"power"` | True | verification。**戻り値は `bool` か `vq.Table[K, bool]` のみ** |
| (4) | `None` | (無視) | ad-hoc。veriq には登録されず、API/CLI 専用 |

### 引数の書き方

#### 単一インスタンス参照
```python
spec: Annotated[BatteryEntry, vq.Ref("$.batteries.main")]
```
→ 「`batteries.main` を指定」と明示。インスタンス名が固定の解析向け。

#### 全インスタンス（Table）
```python
batteries: Annotated[vq.Table[BatteriesName, BatteryEntry], vq.Ref("$.batteries")]
```
→ Web から追加された新インスタンスも自動で含まれる。**集計はこちら**。

#### 直接パラメータ（Ref なし）
```python
mode: OperationMode
years: float = 5.0
```
→ API / CLI から呼び出し時に渡される。input model に組み込まれて Swagger に露出。

### `imports=["orbital"]`

`@vq.Ref(..., scope="orbital")` で他 scope を参照するなら、`imports=` に明示宣言が必須。
無いと veriq が `ValueError` を投げる。

---

## やってはいけないこと

- ❌ `@analysis` 関数内に副作用（TOML 書き込み、HTTP 呼び出し）
- ❌ 戻り値に `dict` / `tuple` / `list`（プリミティブ / Pydantic / `vq.Table` のみ）
- ❌ `verify=True` で戻り値が `bool` 系以外
- ❌ `from __future__ import annotations`

---

## テスト

```python
# tests/unit/analyses/test_power.py
def test_total_power_by_mode():
    from craft.analyses.systems.power import total_power_by_mode

    pdms = vq.Table({
        "main": PDMEntry(spec=..., design=...),
        "aux":  PDMEntry(spec=..., design=...),
    })
    result = total_power_by_mode(pdms=pdms, mode=OperationMode.SAFE)
    assert result == pytest.approx(15.0)
```

@analysis decorator は透過なので、テストは **普通の関数呼び出し**で OK。
