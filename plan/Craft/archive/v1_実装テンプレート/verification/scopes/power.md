---
tags: [project, dev, satellite, template, code]
mirror: verification/scopes/power.py
---

# verification/scopes/power.py

> 親: [[実装テンプレート/README|実装テンプレート]]

veriq の Scope と Project への登録。
**新サブシステムを足す時しか触らない**。`@analysis` を追加するだけなら本ファイルは不要。

---

## ファイル全体

```python
# 重要: from __future__ import annotations は絶対に書かない
"""Power system veriq scope."""

import veriq as vq

from craft.schema._root_model_builder import build_system_root_model
from craft.paths import DATA_ROOT


# Scope オブジェクトを 1 つ作る
power = vq.Scope("power")


# root model を動的に構築して登録
# - registry に登録された全 component を Table として持つ root
# - TOML の現在キーから StrEnum を動的生成
@power.root_model()
class PowerRootModel(build_system_root_model("power", DATA_ROOT / "power.toml")):
    pass
```

---

## 解説

### Scope の登録

```python
power = vq.Scope("power")
```

これだけで veriq の Scope オブジェクトが用意される。
このオブジェクトを `@analysis(system="power", ...)` が **暗黙的に参照** する。

### root model の構築

```python
build_system_root_model("power", DATA_ROOT / "power.toml")
```

内部処理:
1. `default_registry.components(system="power")` で全 component 定義を取得
2. 各 component の `plural` をキーに、 `vq.Table[DynamicEnum, Entry]` フィールドを生やす
3. `DynamicEnum` は `load_instance_enum(toml, plural)` で現在の TOML キーから動的生成
4. `extra="forbid"` を一律適用

### project 登録

`experiment/verification/project.py` 側で:

```python
import veriq as vq

from .scopes.power import power
from .scopes.thermal import thermal      # 追加サブシステムが増えたらここに

project = vq.Project("SpacecraftDesign")
project.add_scope(power)
project.add_scope(thermal)
```

---

## 新サブシステム追加時の手順

1. `schema/systems/<new>.py` を作って `@component` を書く
2. `verification/scopes/<new>.py` を作って scope + root model を登録（本ファイルをコピペ）
3. `verification/project.py` の `project.add_scope(<new>)` を追加

→ **3 ファイル触るだけ**で新サブシステムが API/CLI/MCP/Swagger に自動露出。

---

## やってはいけないこと

- ❌ `from __future__ import annotations` — veriq の inspect.signature が壊れる
- ❌ `@power.calculation` / `@power.verification` を **直接** 書く（→ 必ず `@analysis` 経由）
- ❌ `power.add_calculation(...)` のような直接 API を叩く（registry と veriq の二重登録）
