# Traits リファレンス

Trait は `Component` に共通の振る舞い・フィールドを付与する mixin クラス。
多重継承で宣言するだけで、`Component.__init_subclass__` が MRO を走査して
trait が定義したフィールドを Spec / Design の適切な場所へ自動注入する。

---

## Trait の仕組み

```
class Battery(Component, MultiInstance, TemperatureSensitive):
    ...
```

`Component.__init_subclass__` が呼ばれたとき:

1. `__mro__` を走査し、`_Trait` のサブクラスをすべて列挙
2. 各 trait クラスに通常のフィールドが定義されていれば **Spec** にマージ
3. `__trait_design_extra__` が定義されていれば **Design** にマージ
4. `__trait_no_design__` が `True` なら Design クラス自体を生成しない
5. `__cardinality__` が `"multi"` なら複数インスタンスを許可するフラグを立てる

!!! note "Spec vs Design"
    - **Spec** — コンポーネントの仕様（カタログ値・選定値）。`data.toml` の `[<sub>.<comp>.spec]` セクション
    - **Design** — システム固有の設計値（インスタンスごとに異なる値）。`data.toml` の `[<sub>.<comp>.<instance>.design]` セクション

---

## Component 基底フィールド

Trait とは別に、`Component` を継承したすべてのクラスには以下のフィールドが**常に**自動追加される。

| フィールド | 追加先 | 型 | デフォルト | 説明 |
|---|---|---|---|---|
| `mass_kg` | **Spec** | `float` (ge=0) | `0.0` | 質量 [kg] |
| `quantity` | **Design** | `int` (ge=1) | `1` | 搭載個数 |

これらは `SpecOnly` を含むすべての Component に追加される。

---

## 組み込み Trait 一覧

| Trait | 追加先 | 追加フィールド |
|---|---|---|
| `MultiInstance` | — | フィールドなし（カーディナリティ制御のみ） |
| `PowerConsuming` | Spec + Design | `power_per_unit_w` (Spec), `power_modes` (Design) |
| `TemperatureSensitive` | Spec | `temp_min_c`, `temp_max_c` |
| `SpecOnly` | — | フィールドなし（Design を無効化） |

---

## MultiInstance

```python
class MultiInstance(_Trait):
    __cardinality__: ClassVar[str] = "multi"
```

デフォルトでは Component は Singleton（インスタンス 1 つのみ）として扱われる。
`MultiInstance` を付与するとインスタンスを複数定義できるようになる。

**追加フィールド**: なし（`__cardinality__ = "multi"` フラグのみ）

### 使用例

```python
from schema import Component, MultiInstance, fld

class Battery(Component, MultiInstance):
    capacity_wh: float = fld(ge=0, unit="Wh", desc="Battery capacity")
```

`data.toml` でのインスタンス定義:

```toml
[power.battery.spec]
capacity_wh = 100.0
nominal_voltage_v = 28.0

[power.battery.bat1.design]
depth_of_discharge = 0.7

[power.battery.bat2.design]
depth_of_discharge = 0.65
```

!!! tip "Singleton と MultiInstance の違い"
    - **Singleton**（デフォルト）: `data.toml` に `[<sub>.<comp>.design]` が 1 つ
    - **MultiInstance**: `data.toml` に `[<sub>.<comp>.<instance_name>.design]` が複数

---

## PowerConsuming

```python
class PowerConsuming(_Trait):
    power_per_unit_w: float = fld(
        ge=0, unit="W", desc="単位あたりの想定消費電力"
    )
    __trait_design_extra__: ClassVar[dict] = {
        "power_modes": (
            dict[OperationMode, bool],
            fld(default_factory=dict, desc="OperationMode 別の on/off"),
        ),
    }
```

電力を消費するコンポーネントに付与する。

**追加フィールド**:

| フィールド | 追加先 | 型 | 説明 |
|---|---|---|---|
| `power_per_unit_w` | **Spec** | `float` (ge=0) | 1 ユニットあたりの想定消費電力 (W) |
| `power_modes` | **Design** | `dict[OperationMode, bool]` | 運用モード別の電源 on/off |

`power_modes` のキーは `mission.operation_mode_configs` に定義されたモード名と対応する。
`craft scaffold` を実行すると、登録済みのモード名が dict キーとして自動補完される（`key_source` 機能）。

| キー例 | 意味 |
|---|---|
| `"safe"` | セーフモード |
| `"nominal"` | 通常運用モード |
| `"science"` | 観測モード |
| `"safe_hold"` | セーフホールドモード |

!!! tip "モードの追加・変更"
    `OperationMode` の値は `systems/mission/configs.py` の `OperationModeConfig` インスタンスで管理する。
    新しいモードを追加したら `craft scaffold` を再実行すると `power_modes` に新キーが補完される。

### 使用例

```python
from schema import Component, MultiInstance, PowerConsuming, fld

class PDM(Component, MultiInstance, PowerConsuming):
    """Power Distribution Module。"""
    rated_current_a: float = fld(ge=0, unit="A", desc="定格電流")

    class Design:
        efficiency: float = fld(ge=0, le=1, default=0.95, desc="変換効率")
```

`data.toml` での記述:

```toml
[power.pdm.spec]
power_per_unit_w = 2.5
rated_current_a = 10.0

[power.pdm.pdm_main.design]
efficiency = 0.93
power_modes = { nominal = true, science = true, safe = false, safe_hold = false }
```

!!! note "Design クラスとの共存"
    `PowerConsuming` が注入する `power_modes` は trait の `__trait_design_extra__` 経由で
    Component の `Design` クラスにマージされる。Component 側に `class Design:` を定義しても
    フィールドは上書きされず追加される。

---

## TemperatureSensitive

```python
class TemperatureSensitive(_Trait):
    temp_min_c: float = fld(unit="degC", desc="動作温度下限")
    temp_max_c: float = fld(unit="degC", desc="動作温度上限")
```

動作温度範囲を持つコンポーネントに付与する。

**追加フィールド**（いずれも **Spec** に注入、required）:

| フィールド | 型 | 単位 | 説明 |
|---|---|---|---|
| `temp_min_c` | `float` | degC | 動作温度下限 |
| `temp_max_c` | `float` | degC | 動作温度上限 |

### 使用例

```python
from schema import Component, MultiInstance, TemperatureSensitive, fld

class Battery(Component, MultiInstance, TemperatureSensitive):
    """二次電池。"""
    capacity_wh: float = fld(ge=0, unit="Wh", desc="Battery capacity")
    nominal_voltage_v: float = fld(ge=0, unit="V", default=0.0)
```

`data.toml` での記述（`TemperatureSensitive` が追加した 2 フィールドを含む）:

```toml
[power.battery.spec]
capacity_wh = 100.0
nominal_voltage_v = 28.0
temp_min_c = -20.0
temp_max_c = 40.0
```

!!! tip "Spec のみへの注入"
    `TemperatureSensitive` が追加するフィールドは Spec のみ。
    インスタンスごとに動作温度を変えたい場合は、Component 側の `Design` クラスに
    個別フィールドを追加すること。

---

## SpecOnly

```python
class SpecOnly(_Trait):
    __trait_no_design__: ClassVar[bool] = True
```

Design セクションを持たない「データシート型」コンポーネントに付与する。
`__init_subclass__` は `__trait_no_design__ = True` を検出すると
`Design` クラスの生成をスキップする。

**追加フィールド**: なし

### 使用例

```python
from schema import Component, SpecOnly, fld

class Gyroscope(Component, SpecOnly):
    """ジャイロスコープ（仕様のみ、設計値なし）。"""
    noise_density_dps_sqrthz: float = fld(
        unit="dps/sqrt(Hz)", desc="角速度ノイズ密度"
    )
    full_scale_dps: float = fld(gt=0, unit="dps", desc="フルスケール角速度")
    mass_g: float = fld(ge=0, unit="g", desc="質量")
```

`data.toml` では `design` セクションなしで使う:

```toml
[adcs.gyroscope.spec]
noise_density_dps_sqrthz = 0.005
full_scale_dps = 300.0
mass_g = 12.5
```

!!! note "SpecOnly と他 trait の組み合わせ"
    `SpecOnly` は他の trait と組み合わせられる。例えば `SpecOnly` + `MultiInstance` で
    「複数インスタンスを持てるが Design は不要なコンポーネント」を表現できる。

---

## Trait の組み合わせ

実際のコンポーネントでよく使う組み合わせ:

| 組み合わせ | 典型的な用途 |
|---|---|
| `MultiInstance` | 同型部品の複数搭載（バッテリ、スラスタ等） |
| `MultiInstance` + `TemperatureSensitive` | バッテリ、太陽電池など |
| `MultiInstance` + `PowerConsuming` | PDM、通信機など |
| `MultiInstance` + `TemperatureSensitive` + `PowerConsuming` | 観測機器、大型電子機器など |
| `SpecOnly` | データシートから仕様を読むだけの部品 |
| `SpecOnly` + `MultiInstance` | 同型の受動部品を複数搭載する場合 |

```python
# 典型例: バッテリ（複数搭載・温度管理あり）
class Battery(Component, MultiInstance, TemperatureSensitive):
    capacity_wh: float = fld(ge=0, unit="Wh")
    nominal_voltage_v: float = fld(ge=0, unit="V", default=0.0)

# 典型例: 電力分配モジュール（複数搭載・消費電力あり）
class PDM(Component, MultiInstance, PowerConsuming):
    rated_current_a: float = fld(ge=0, unit="A")

# 典型例: 太陽電池（複数搭載・温度管理あり・消費電力なし）
class SolarPanel(Component, MultiInstance, TemperatureSensitive):
    area_m2: float = fld(ge=0, unit="m^2")
    efficiency: float = fld(ge=0, le=1, default=0.28)

# 典型例: カタログ部品（仕様のみ）
class MagnetTorquer(Component, SpecOnly, MultiInstance):
    dipole_moment_am2: float = fld(gt=0, unit="A*m^2")
    mass_g: float = fld(ge=0, unit="g")
```

---

## カスタム Trait の作り方

`_Trait` を継承してフィールドや ClassVar を定義するだけで独自 trait を作れる。

### パターン 1: Spec にフィールドを追加

```python
from typing import ClassVar
from schema.traits import _Trait
from schema.fields import fld

class Redundant(_Trait):
    """冗長系を持つコンポーネント。"""
    redundancy_level: int = fld(ge=1, default=2, desc="冗長度")
    hot_standby: bool = fld(default=False, desc="ホットスタンバイか")
```

使い方:

```python
class OnboardComputer(Component, MultiInstance, Redundant):
    clock_mhz: float = fld(gt=0, unit="MHz")
```

### パターン 2: Design にフィールドを追加（`__trait_design_extra__`）

`__trait_design_extra__` は `{"field_name": (type, fld(...))}` の辞書として定義する。

```python
from typing import Any, ClassVar
from schema.traits import _Trait
from schema.fields import fld

class ModeAware(_Trait):
    """運用モード依存の振る舞いを持つコンポーネント。"""
    __trait_design_extra__: ClassVar[dict[str, Any]] = {
        "active_in_safe_mode": (
            bool,
            fld(default=False, desc="セーフモードでも動作するか"),
        ),
    }
```

### パターン 3: フラグのみ（`__trait_no_design__` など）

動作変更だけが目的でフィールド追加が不要な場合は ClassVar フラグのみ定義する。

```python
class ExternalInterface(_Trait):
    """外部とのインターフェースを持つコンポーネントのマーカー。"""
    __is_external_interface__: ClassVar[bool] = True
```

!!! warning "カスタム Trait と `__init_subclass__`"
    `__trait_design_extra__` / `__trait_no_design__` / `__cardinality__` の 3 つは
    `Component.__init_subclass__` が明示的に認識するフラグ名。
    独自の ClassVar フラグを追加してもフレームワーク側は無視するため、
    活用するには `__init_subclass__` 側の拡張も必要になる。

---

## `from __future__ import annotations` 禁止

!!! warning "trait の定義でも `from __future__ import annotations` は書かない"
    フィールド型ヒントが文字列として保留されると、
    veriq の `inspect.signature()` が実行時に型を解決できなくなる。
    trait ファイルも含め、プロジェクト全体でこの import は禁止。
