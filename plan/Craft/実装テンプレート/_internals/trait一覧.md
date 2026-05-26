---
tags: [project, dev, satellite, template, internals]
mirror: schema/traits.py
---

# schema/traits.py — Trait 一覧

> 親: [[実装テンプレート/README|実装テンプレート]]
> 関連: [[実装テンプレート/_internals/Component基底]]

ユーザが多重継承で混ぜる **マーカークラス群**。各 trait が **どんな field を生やすか** を一覧化。

---

## ファイル全体

```python
"""Component traits.

trait は Component と組み合わせて多重継承で混ぜる。
Component.__init_subclass__ が __mro__ を走査して trait を検出し、
それぞれの trait が宣言した field を Spec / Design / Requirements にマージする。
"""

from craft.schema.fields import fld
from craft.schema.common import OperationMode


class PowerConsuming:
    """電力を消費する component を示す。

    自動付与:
    - Spec: default_power_consumption_per_unit_w
    - Design: power_modes (= 旧 HasPowerMode の効果を吸収)

    「電力を消費するなら必ず OperationMode 別の on/off を定義する」という規約。
    """

    # Spec 側
    default_power_consumption_per_unit_w: float = fld(
        ge=0,
        unit="W",
        desc="単位あたりの想定消費電力",
    )

    # Design 側に追加する field (Component.__init_subclass__ が解釈)
    __trait_design_extra__ = {
        "power_modes": fld(
            default_factory=dict,
            desc="OperationMode 別の on/off",
        ),
    }


# （旧 PowerGenerating は廃止。発電 component は SolarPanel しか存在しないため、
#  trait として抽象化する価値が薄い。SolarPanel が直接 field を持つ。）


class TemperatureSensitive:
    """動作温度範囲を持つ component を示す。"""

    operating_temperature_min_c: float = fld(
        unit="degC",
        desc="動作温度下限",
    )
    operating_temperature_max_c: float = fld(
        unit="degC",
        desc="動作温度上限",
    )


# （旧 HasPowerMode は PowerConsuming に統合済み。
#  「電力を消費する → mode 別 on/off が必須」という規約のため。）


class SpecOnly:
    """Design を持たない component を示す（旧 `Datasheet`）。

    Component.__init_subclass__ が Design 自動生成をスキップする。
    PanelSurface のような material library 用途。
    """

    __trait_no_design__ = True


class MultiInstance:
    """インスタンスを複数許可する component。

    default の Singleton（インスタンスキー無し、`[obc.spec]` フラット）から、
    `[batteries.<name>.spec]` のような複数 instance 階層に切り替える。

    `shared_spec` (default True) で spec を全 instance で共有するかを制御。

    TOML 構造:
        [batteries.spec]         # shared_spec=True（共有）
        [batteries.main.design]
        [batteries.aux.design]
    """

    __cardinality__ = "multi"
    __shared_spec_default__ = True


```

> **default は Singleton**（trait 不要、TOML が `[obc.spec]` フラット）。複数積む場合のみ `MultiInstance` を継承する。
> 旧 `Singleton` trait は廃止（default のため不要）。
> 旧 `WithDatasheet` trait（spec を `<plural>_datasheets` テーブルに切り出す案）も **採用見送り**。
> 「同型製品の共通 spec」は `MultiInstance` + default の `shared_spec=True` で実現する
> （[[宣言とTOMLの対応表]] §P3、archive [[Datasheet設計]]）。

---

## Trait 効果まとめ

| Trait | 影響先 | 追加されるもの |
|---|---|---|
| (なし、default) | cardinality | **Singleton**: TOML フラット (`[obc.spec]`)、インスタンスキー無し |
| `MultiInstance` | cardinality | 複数 instance 許可（plural テーブル名、`[batteries.<name>...]`、`shared_spec` 引数有効化）→ [[インスタンス多重度]] |
| `PowerConsuming` | `Spec` + `Design` | Spec: `default_power_consumption_per_unit_w`、Design: `power_modes: dict[OperationMode, bool]` |
| `TemperatureSensitive` | `Spec` | `operating_temperature_min_c`, `operating_temperature_max_c` |
| `SpecOnly` (旧 `Datasheet`) | (フラグ) | `Design` 自動生成をスキップ |

⚠️ 旧 `HasPowerMode` は **`PowerConsuming` に統合**。「電力消費するなら必ず power_modes を持つ」という規約。
⚠️ 旧 `PowerGenerating` は **廃止**。発電 component は SolarPanel しか存在しないため、SolarPanel が直接 `default_power_generation_per_unit_w` field を持つ。

---

## 組み合わせのルール

### 衝突する組み合わせ

| 組み合わせ | 結果 |
|---|---|
| `PowerConsuming` + `SpecOnly` | ❌ 矛盾。`PowerConsuming` は Design に `power_modes` を追加する一方 `SpecOnly` は Design 無し → `TraitConflict` |
| Singleton (default) + `SpecOnly` | ✅ OK。Design 不要の 1 機構成 (BusStructure 等) |
| `MultiInstance` + `SpecOnly` | ✅ OK。複数積み + Design 無し（material library 等）。自動的に `shared_spec=False` 強制 |
| `MultiInstance` + 他 trait | ✅ OK。MultiInstance はカーディナリティのみ規定 |
| 同一 trait の重複 | OK、idempotent |

### MRO 順序の影響

Python の MRO は **左から解決**。component の宣言:
```python
class Battery(Component, TemperatureSensitive):
    ...
```
で `Component` が左、trait が右。`Component.__init_subclass__` が `__mro__` を走査するので順序は影響しないが、 **`Component` を必ず最左に書く規約** とする（人間の読みやすさのため）。

---

## ユーザが新 trait を作りたい時

`systems/` に trait は置かない。新 trait は **schema/traits.py に追加** する（共通基盤）。

最小サンプル:
```python
class Radiation Sensitive:
    """放射線環境耐性の特性を持つ"""
    total_dose_krad_max: float = fld(ge=0, unit="krad")
```

追加後、対応する全 component で:
```python
class Battery(Component, TemperatureSensitive, RadiationSensitive):
    ...
```
と書ける。

---

## やってはいけないこと

- ❌ trait 内で `class Design:` / `class Requirements:` を書く（trait は flat な属性集合のみ）
- ❌ trait に method を実装する（marker / field declaration のみ）
- ❌ trait を `Component` 派生にする（trait の純粋性を保つ）
- ❌ system 配下で trait を定義（共通基盤に置く規約）
