# Analysis の書き方

`@analysis` デコレータで登録した関数は、veriq の計算・検証パイプラインに組み込まれる。
このガイドでは、実際のコード例を通して「veriq バインド型」と「ad-hoc 型」の2パターンを詳しく説明する。

---

## 2種類の Analysis

| 種類 | `system` | 実行方法 | 用途 |
|---|---|---|---|
| **veriq バインド型** | system 名（自動推論） | `craft verify` / `craft analysis run <sub> <name>` | 設計検証・計算 |
| **ad-hoc 型** | `None`（明示指定） | `craft analysis run _ <name> --payload '{...}'` | 独立した計算ユーティリティ |

---

## veriq バインド型 Analysis

veriq のデータグラフに束縛される Analysis。引数は `Annotated[型, vq.Ref("パス")]` で宣言し、veriq がデータを注入する。

### 基本パターン

```python
from typing import Annotated
import veriq as vq
from schema import analysis


@analysis(desc="全バッテリの使用可能容量合計 (Wh)")
def total_available_capacity_wh(
    batteries: Annotated[vq.Table, vq.Ref("$.batteries")],  # (1)
) -> float:
    return sum(
        b.spec.capacity_wh * b.requirements.depth_of_discharge_max
        for b in batteries.values()
    )
```

1. `vq.Ref("$.batteries")` — 現在スコープの `batteries` テーブルを参照

### vq.Ref のパス構文

| パス | 意味 | 型 |
|---|---|---|
| `$.batteries` | 現在スコープの `batteries` テーブル（MultiInstance） | `vq.Table` |
| `$.obc` | 現在スコープの `obc`（Singleton） | モデルインスタンス |
| `$.mission_config` | 現在スコープの Config | モデルインスタンス |
| `@total_pdm_power_w` | 同スコープの calculation 結果を参照 | calculation の戻り値型 |
| `$.orbitalparams.eclipse_duration_s` (scope=...) | 別スコープのフィールド（後述） | フィールドの型 |

!!! note "パスの `$` は「このスコープのルート」"
    `$` は veriq の JMESPath-like 記法でスコープルートを指す。
    component の plural キー（`batteries`, `solar_panels` 等）をそのまま使う。

### calculation 結果を参照する

別の calculation の結果値を引数として受け取れる（`@名前` 記法）:

```python
@analysis(desc="全 PDM 消費電力合計 (W)")
def total_pdm_power_w(
    pdms: Annotated[vq.Table, vq.Ref("$.pdms")],
) -> float:
    return sum(
        p.spec.power_per_unit_w
        for p in pdms.values()
        if p.design.power_modes.get("nominal", False)
    )


@analysis(
    desc="eclipse 中に必要なエネルギー量 (Wh)",
    imports=["orbital"],  # (1)
)
def required_orbit_energy_wh(
    pdm_power: Annotated[float, vq.Ref("@total_pdm_power_w")],         # (2)
    eclipse_s: Annotated[float, vq.Ref(                                  # (3)
        "$.orbitalparams.eclipse_duration_s", scope="orbital"
    )],
) -> float:
    return pdm_power * eclipse_s / 3600.0
```

1. `imports=["orbital"]` — 他 system のデータを使う場合に宣言
2. `@total_pdm_power_w` — 同スコープの calculation 結果を参照
3. `scope="orbital"` — 別スコープのフィールドを参照

### verification（`verify=True`）

戻り値が `bool` の Analysis。veriq の verification として登録され、`craft verify` で ✓/✗ が表示される。

```python
@analysis(verify=True, desc="全バッテリが容量要件を満たすか")
def verify_battery_capacity(
    batteries: Annotated[vq.Table, vq.Ref("$.batteries")],
) -> bool:
    required_wh = 50.0
    if not batteries:
        return False
    return all(
        b.spec.capacity_wh * b.requirements.depth_of_discharge_max >= required_wh
        for b in batteries.values()
    )
```

```
  VERI ✓ power/?verify_battery_capacity  =  True
```

!!! warning "veriq バインド型で重要な制約"
    引数は必ず `Annotated[型, vq.Ref(...)]` で宣言すること。
    生のパラメータ（`def func(capacity: float)`）は veriq に渡せない。
    生パラメータが必要な場合は **ad-hoc 型** を使う。

---

## ad-hoc 型 Analysis

veriq に依存しない独立した計算関数。`system=None` で登録し、CLI から直接引数を渡して実行できる。

```python
@analysis(
    system=None,         # (1)
    desc="バッテリ EOL 容量推定",
    cache=True,             # (2)
)
def battery_eol_capacity(
    initial_capacity_wh: float,             # (3)
    years: float = 5.0,
    cycles_per_day: float = 1.0,
) -> float:
    """初期容量と寿命・サイクル数から degradation を加味した EOL 容量を返す。"""
    cycles_total = years * 365.0 * cycles_per_day
    degradation = min(0.2, 0.0001 * cycles_total)
    return initial_capacity_wh * (1.0 - degradation)
```

1. `system=None` — veriq 非登録、`craft verify` には含まれない
2. `cache=True` — 同じ引数での再実行はキャッシュから返す
3. 生のパラメータ — `--payload` JSON で渡す

実行:

```bash
uv run craft analysis run _ battery_eol_capacity \
  --payload '{"initial_capacity_wh": 100.0, "years": 3.0}'
```

```json
{
  "value": 89.075,
  "cache_hit": false
}
```

---

## 2パターンの比較

```python
# ─── veriq バインド型 ─────────────────────────────────────────────────
@analysis(desc="設計検証・計算")
def my_calc(
    batteries: Annotated[vq.Table, vq.Ref("$.batteries")],  # veriq が注入
) -> float:
    ...

# ─── ad-hoc 型 ────────────────────────────────────────────────────────
@analysis(system=None, desc="独立ユーティリティ")
def my_util(
    capacity: float,        # CLI --payload で渡す
    factor: float = 0.9,
) -> float:
    ...
```

| 比較軸 | veriq バインド型 | ad-hoc 型 |
|---|---|---|
| `craft verify` に含まれる | ✓ | ✗ |
| `craft analysis run` で実行できる | ✓ | ✓ |
| 引数の渡し方 | `vq.Ref` で自動注入 | `--payload JSON` |
| 他スコープ参照 | `imports=[]` で可能 | 不可 |
| キャッシュ | ✗ | `cache=True` で可能 |

---

## よくあるパターン

### MultiInstance テーブルの集計

```python
@analysis(desc="最大トルク合計 (N·m)")
def total_torque_nm(
    reaction_wheels: Annotated[vq.Table, vq.Ref("$.reaction_wheels")],
) -> float:
    return sum(rw.spec.max_torque_nm for rw in reaction_wheels.values())
```

### Singleton へのアクセス

```python
@analysis(desc="軌道周期 (s)")
def orbital_period_s(
    params: Annotated[object, vq.Ref("$.orbitalparams")],
) -> float:
    import math
    mu = 3.986e14  # Earth GM
    r = (params.altitude_km + 6371) * 1e3
    return 2 * math.pi * math.sqrt(r**3 / mu)
```

### verification で Singleton と MultiInstance を組み合わせる

```python
@analysis(verify=True, desc="バッテリ総容量がミッション要件を満たすか")
def verify_total_capacity(
    batteries: Annotated[vq.Table, vq.Ref("$.batteries")],
    mission: Annotated[object, vq.Ref("$.mission_config", scope="mission")],
    eclipse_wh: Annotated[float, vq.Ref("@required_orbit_energy_wh")],
) -> bool:
    total = sum(b.spec.capacity_wh for b in batteries.values())
    return total >= eclipse_wh * mission.margin_factor
```

---

## scope.py への登録（自動）

`@analysis` を追加するだけで scope.py が自動的に veriq に登録する。**scope.py の編集は不要**。

```python
# scope.py が自動で行う処理
for adef in default_registry.analyses(system="power"):
    if adef.verify:
        power.verification(adef.name, imports=adef.imports)(adef.func)
    else:
        power.calculation(adef.name, imports=adef.imports)(adef.func)
```
