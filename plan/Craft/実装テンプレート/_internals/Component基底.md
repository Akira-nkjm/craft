---
tags: [project, dev, satellite, template, internals]
mirror: schema/_component.py
---

# schema/_component.py — Component 基底クラス

> 親: [[実装テンプレート/README|実装テンプレート]]
> 関連: [[型検証と宣言方式]] / [[UnifiedRegistry設計]]

ユーザは直接触らない。 **挙動を理解するため** に読むファイル。

---

## 役割

`Component` は **3 つの役割** を 1 クラスに集約:

1. `__init_subclass__` で派生クラス（`Battery` 等）の作成を hook
2. Pydantic モデル (`Spec` / `Design` / `Requirements` / `Entry`) を **属性として生やす**
3. `UnifiedRegistry` に自動登録

加えて `dataclass_transform` で pyrefly に「dataclass-like」と通知。

---

## 実装スケッチ

```python
"""Component base class."""

from __future__ import annotations  # ← ここは OK（veriq scope ファイルではない）

import inspect
from pathlib import Path
from typing import Any, ClassVar, dataclass_transform

from pydantic import BaseModel, ConfigDict, create_model

from craft.schema._registry import default_registry
from craft.schema._definition import ComponentDefinition, SourceLocation
from craft.schema.fields import fld


@dataclass_transform(field_specifiers=(fld,))
class Component:
    """全 component の基底クラス。decorator なしで使う。"""

    # 派生クラスが持つ属性（生成後に attach される）
    Spec: ClassVar[type[BaseModel]]
    Design: ClassVar[type[BaseModel]]
    Requirements: ClassVar[type[BaseModel] | None]
    Entry: ClassVar[type[BaseModel]]

    # registry に登録された情報
    __subsystem__: ClassVar[str]
    __plural__: ClassVar[str]

    def __init_subclass__(
        cls,
        *,
        subsystem: str | None = None,
        plural: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)

        # trait base class そのものや internal class はスキップ
        if cls.__name__.startswith("_") or _is_internal_trait_class(cls):
            return

        # subsystem を自動推論 or 明示値を採用
        if subsystem is None:
            subsystem = _infer_subsystem_from_caller()

        # plural を自動推論 or 明示
        if plural is None:
            plural = _auto_pluralize(cls.__name__)

        # trait を MRO から集める
        traits = [b for b in cls.__mro__ if _is_trait(b)]

        # field 宣言を MRO 経由で集約し、Pydantic models を build
        spec = _build_spec_model(cls, traits)
        design = _build_design_model(cls, traits)
        requirements = _build_requirements_model(cls)
        entry = _build_entry_model(cls, spec, design, requirements)

        # cls の属性として attach
        cls.Spec = spec
        cls.Design = design
        cls.Requirements = requirements
        cls.Entry = entry
        cls.__subsystem__ = subsystem
        cls.__plural__ = plural

        # registry 登録
        defn = ComponentDefinition(
            subsystem=subsystem,
            name=cls.__name__.lower(),
            plural=plural,
            spec=spec,
            design=design,
            requirements=requirements,
            entry=entry,
            cls=cls,
            traits=tuple(t.__name__ for t in traits),
            source=SourceLocation.of(cls),
            desc=cls.__doc__,
        )
        default_registry.register_component(defn)
```

---

## ポイント

### `dataclass_transform`

```python
@dataclass_transform(field_specifiers=(fld,))
class Component:
    ...
```

PEP 681 のマーカー。pyrefly / pyright / mypy に「`fld()` は dataclass の field 指定」と伝える。これにより:

- `Battery(capacity_wh=100, nominal_voltage_v=3.7)` のコンストラクタ補完
- field の型・default・制約が型チェッカに見える
- gen_stubs に頼らずに大半の型情報が取れる

### `__init_subclass__`

PEP 487 で導入された **「サブクラス化時のフック」**。

```python
class Battery(Component, TemperatureSensitive):
    ...
```

を書いた瞬間、 `Component.__init_subclass__(cls=Battery)` が呼ばれる。
decorator と違って **クラス本体の解釈は標準ルールのまま**、追加処理だけ挟む。

### キーワード引数の伝播

```python
class Battery(Component, TemperatureSensitive, subsystem="power_alt", plural="batteries"):
    ...
```

PEP 487 はクラス定義時のキーワード引数を `__init_subclass__` に転送する仕様。
→ `subsystem` と `plural` を **クラス定義の最後にキーワード引数として** 書ける。

### subsystem 自動推論

```python
def _infer_subsystem_from_caller() -> str:
    """呼び出し元ファイルパスから subsystem を推論。"""
    frame = inspect.currentframe()
    # __init_subclass__ → Component → class body の順にスタックを辿る
    while frame:
        path = Path(frame.f_code.co_filename)
        if "subsystems" in path.parts:
            idx = path.parts.index("subsystems")
            return path.parts[idx + 1]  # "power"
        frame = frame.f_back
    raise RuntimeError("Cannot infer subsystem; pass explicitly")
```

### trait からの field 集約

```python
class TemperatureSensitive:
    """trait: 動作温度範囲を持つ"""
    operating_temperature_min_c: float = fld(unit="degC")
    operating_temperature_max_c: float = fld(unit="degC")
```

trait class の field 宣言を `cls.__mro__` 経由で集めて、`Spec` model に統合。Python の MRO で自然に解決されるので衝突時の挙動も予測可能。

---

## ユーザから見える挙動

```python
# 定義
class Battery(Component, TemperatureSensitive):
    capacity_wh: float = fld(ge=0, unit="Wh")

# 自動的に生える
Battery.Spec           # Spec model
Battery.Design         # Design model（空ならからの BaseModel）
Battery.Requirements   # Requirements or None
Battery.Entry          # ComponentEntry 統合 model
Battery.__subsystem__  # "power"  (自動推論)
Battery.__plural__     # "batteries"

# pydantic v2 直接使用可
b = Battery.Entry.model_validate({"spec": {...}, "design": {...}})
b.model_dump_json()

# registry にも登録済み
from craft.schema import default_registry
defn = default_registry.component("power", "battery")
```

---

## やってはいけないこと（実装側）

- ❌ `__init_subclass__` 内で **副作用のある I/O**（registry 登録以外）
- ❌ trait class を Component 派生にする → 循環、二重登録
- ❌ subsystem 自動推論を最終 fallback 無しで実装（テスト時にスタック追跡できないと爆発）
