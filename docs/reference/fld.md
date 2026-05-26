# fld() リファレンス

`fld()` は `Component` / `Config` / `Analysis` のフィールド宣言に使うヘルパー関数。
Pydantic の `Field()` への薄いラッパで、物理単位・UI グループ・表示順序などのメタデータを
`json_schema_extra` に乗せる。

---

## クイックリファレンス

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `default` | `Any` | `...`（必須） | スカラーなデフォルト値。省略すると required フィールドになる |
| `default_factory` | `callable \| None` | `None` | 可変なデフォルト（`list`, `dict` など）に使うファクトリ関数 |
| `ge` | `float \| None` | `None` | 以上（greater-or-equal）制約 |
| `le` | `float \| None` | `None` | 以下（less-or-equal）制約 |
| `gt` | `float \| None` | `None` | より大きい（greater-than）制約 |
| `lt` | `float \| None` | `None` | より小さい（less-than）制約 |
| `unit` | `str \| None` | `None` | 物理単位文字列（例: `"W"`, `"Wh"`, `"degC"`）。JSON Schema / Swagger UI に表示される |
| `desc` | `str \| None` | `None` | フィールドの説明文。JSON Schema の `description` になる |
| `group` | `str \| None` | `None` | UI 上のグループ名。`json_schema_extra` に格納 |
| `order` | `int \| None` | `None` | UI 上の表示順序。`json_schema_extra` に格納 |

!!! note "戻り値の型は `Any`"
    実体は Pydantic の `FieldInfo` だが、戻り値型は `Any` と宣言されている。
    これは `dataclass_transform` の field_specifier として動作させつつ、
    pyrefly / mypy が `FieldInfo` をフィールド型に誤検出するのを防ぐため。

---

## インポート

```python
from schema import fld
# または
from schema.fields import fld
```

---

## パラメータ詳細

### `default` — デフォルト値

省略すると `...`（Ellipsis）が渡され、Pydantic は required フィールドとして扱う。

```python
# required（デフォルトなし）
capacity_wh: float = fld(unit="Wh", desc="Battery capacity")

# optional（デフォルトあり）
efficiency: float = fld(default=0.28, desc="セル効率")
```

### `default_factory` — 可変なデフォルト

`list` や `dict` は `default=[]` のように直接渡せない（Pydantic の共有ミュータブル問題）。
`default_factory` を使う。

```python
power_modes: dict[OperationMode, bool] = fld(
    default_factory=dict,
    desc="OperationMode 別の on/off",
)
tags: list[str] = fld(default_factory=list)
```

!!! warning "`default` と `default_factory` は同時に指定しない"
    両方を指定すると Pydantic がエラーを発生させる。
    `fld()` 内部でも `default_factory` が `None` でない場合は `default` を渡さない実装になっている。

### 数値制約 — `ge`, `le`, `gt`, `lt`

Pydantic の `Field(ge=...)` に直接対応する。

| 引数 | 意味 | 例 |
|---|---|---|
| `ge` | `value >= ge` | `fld(ge=0)` — 非負 |
| `le` | `value <= le` | `fld(le=1)` — 1 以下 |
| `gt` | `value > gt` | `fld(gt=0)` — 正 |
| `lt` | `value < lt` | `fld(lt=100)` — 100 未満 |

組み合わせてレンジ指定も可能:

```python
depth_of_discharge: float = fld(ge=0, le=1, desc="設計時 DoD")
rated_voltage_v: float = fld(gt=0, lt=60, unit="V")
```

### `unit` — 物理単位

`json_schema_extra["unit"]` に格納され、JSON Schema と Swagger UI で表示される。
単位文字列の正規形は特に規定しないが、プロジェクト内での一貫性を保つこと。

よく使う単位文字列の例:

| 単位 | 文字列 |
|---|---|
| ワット | `"W"` |
| ワット時 | `"Wh"` |
| ボルト | `"V"` |
| アンペア | `"A"` |
| 摂氏 | `"degC"` |
| 平方メートル | `"m^2"` |
| キログラム | `"kg"` |
| 秒 | `"s"` |
| ビット毎秒 | `"bps"` |

```python
area_m2: float = fld(ge=0, unit="m^2", desc="Panel area")
```

### `desc` — 説明文

Pydantic `Field(description=...)` に対応。JSON Schema の `description` キーになり、
Swagger UI のモデルビューや `craft schema show` の出力に現れる。

```python
manufacturer: str = fld(default="", desc="Manufacturer name")
```

### `group` / `order` — UI ヒント

`json_schema_extra["group"]` / `json_schema_extra["order"]` に格納される。
FastAPI / Swagger UI の表示や将来の GUI ツールでのフィールドグルーピング・ソートに使う。

```python
class ThermalCoating(Component):
    absorptivity: float = fld(ge=0, le=1, group="optical", order=1)
    emissivity: float = fld(ge=0, le=1, group="optical", order=2)
    thickness_mm: float = fld(ge=0, unit="mm", group="physical", order=1)
```

---

## 使用例

### 必須フィールド（デフォルトなし）

```python
from schema import Component, fld

class Battery(Component):
    capacity_wh: float = fld(ge=0, unit="Wh", desc="Battery capacity")
    nominal_voltage_v: float = fld(ge=0, unit="V", desc="公称電圧")
```

インスタンス化時に必ず値を与える必要がある:

```python
# OK
b = Battery(capacity_wh=100.0, nominal_voltage_v=28.0)

# Pydantic ValidationError
b = Battery()
```

### デフォルト値付きフィールド

```python
class SolarPanel(Component):
    efficiency: float = fld(ge=0, le=1, default=0.28, desc="セル効率")
    manufacturer: str = fld(default="", desc="Manufacturer")
```

### 数値制約付きフィールド

```python
class Battery(Component):
    class Design:
        depth_of_discharge: float = fld(ge=0, le=1, desc="設計時 DoD")

    class Requirements:
        depth_of_discharge_max: float = fld(
            default=0.8, gt=0, le=1, desc="要求 DoD 上限"
        )
```

### 単位・説明付きフィールド

```python
class ThermalRadiator(Component):
    area_m2: float = fld(ge=0, unit="m^2", desc="放熱面積")
    emissivity: float = fld(ge=0, le=1, desc="表面放射率")
    operating_temperature_min_c: float = fld(unit="degC", desc="最低動作温度")
    operating_temperature_max_c: float = fld(unit="degC", desc="最高動作温度")
```

### グループ・表示順付きフィールド

```python
class Antenna(Component):
    gain_dbi: float = fld(unit="dBi", group="rf", order=1, desc="アンテナ利得")
    frequency_mhz: float = fld(gt=0, unit="MHz", group="rf", order=2, desc="周波数")
    mass_kg: float = fld(ge=0, unit="kg", group="physical", order=1, desc="質量")
```

### 可変デフォルト（`default_factory`）

```python
from schema.common import OperationMode

class Controller(Component):
    class Design:
        enabled_modes: dict[OperationMode, bool] = fld(
            default_factory=dict,
            desc="モード別の有効/無効フラグ",
        )
        telemetry_channels: list[str] = fld(
            default_factory=list,
            desc="送信するテレメトリチャンネルのリスト",
        )
```

---

## よくある書き方パターン

### 温度フィールド

```python
class TemperatureLimits(Component):
    min_temp_c: float = fld(unit="degC", desc="最低動作温度")
    max_temp_c: float = fld(unit="degC", desc="最高動作温度")
    survival_min_c: float = fld(unit="degC", desc="サバイバル温度下限")
    survival_max_c: float = fld(unit="degC", desc="サバイバル温度上限")
```

!!! tip "TemperatureSensitive trait"
    動作温度の上下限が必要なだけなら `TemperatureSensitive` trait を使うと
    `operating_temperature_min_c` / `operating_temperature_max_c` が自動追加される。
    詳細は [Traits リファレンス](traits.md) を参照。

### 電力フィールド

```python
class PowerComponent(Component):
    rated_power_w: float = fld(ge=0, unit="W", desc="定格電力")
    peak_power_w: float = fld(ge=0, unit="W", desc="ピーク電力")
    standby_power_w: float = fld(ge=0, unit="W", default=0.0, desc="待機電力")
```

!!! tip "PowerConsuming trait"
    電力消費コンポーネントには `PowerConsuming` trait を使うと
    `default_power_consumption_per_unit_w` と `power_modes` が自動追加される。
    詳細は [Traits リファレンス](traits.md) を参照。

### 比率・効率フィールド（0〜1）

```python
class Converter(Component):
    efficiency: float = fld(ge=0, le=1, default=0.95, desc="変換効率")
    duty_cycle: float = fld(ge=0, le=1, desc="デューティサイクル")
```

### 整数カウントフィールド

```python
class Array(Component):
    cell_count: int = fld(ge=1, desc="セル数")
    string_count: int = fld(ge=1, desc="ストリング数")
    redundancy: int = fld(ge=0, default=0, desc="冗長系数")
```

---

## `from __future__ import annotations` 禁止

!!! warning "`from __future__ import annotations` は書かない"
    Craft では `from __future__ import annotations` の使用を**禁止**している。

    これを書くと Python が型ヒントを実行時に評価せず文字列として扱うため、
    veriq が `inspect.signature()` 経由で実行時に型を読もうとした際に
    前方参照の解決に失敗し、検証パイプラインが壊れる。

    型ヒントは常に実体（具体的な型）を直接書くこと。

    ```python
    # NG — veriq が壊れる
    from __future__ import annotations
    from schema import Component, fld

    # OK
    from schema import Component, fld
    ```

---

## 実装詳細

`fld()` の内部動作:

1. `unit`, `group`, `order` が指定されていれば `json_schema_extra` 辞書に格納
2. `default_factory` が指定されていれば `kwargs["default_factory"]` に渡す（`default` は渡さない）
3. `ge`, `le`, `gt`, `lt`, `desc` は `None` でなければ対応する Pydantic キーに渡す
4. 最終的に `pydantic.Field(**kwargs)` を呼び出して結果を返す

```python
# fld(ge=0, unit="W", desc="消費電力") は内部的にこう展開される:
Field(
    default=...,
    ge=0,
    description="消費電力",
    json_schema_extra={"unit": "W"},
)
```

`Component` / `Config` クラスは `@dataclass_transform(field_specifiers=(fld,))` で
デコレートされているため、型チェッカーは `fld()` をフィールド宣言として認識する。
