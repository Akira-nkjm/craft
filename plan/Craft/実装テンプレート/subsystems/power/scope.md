---
tags: [project, dev, satellite, template, code]
mirror: subsystems/power/scope.py
---

# subsystems/power/scope.py

> 親: [[実装テンプレート/README|実装テンプレート]]

veriq `Scope` の定義。 **新サブシステムを足す時だけ触る**。component や analysis を追加するだけなら本ファイルは不要。

---

## ファイル全体

```python
# 注意: from __future__ import annotations は絶対に書かない
"""Power subsystem veriq scope."""

import veriq as vq

from craft.schema import build_subsystem_root_model
from craft.paths import subsystem_data_path


# Scope オブジェクト (subsystem 名と一致させる)
power = vq.Scope("power")


# root model: registry の現在の component 群 + TOML の現在の instance キーから動的構築
@power.root_model()
class PowerRootModel(build_subsystem_root_model("power", subsystem_data_path("power"))):
    pass
```

---

## 解説

### Scope の登録

```python
power = vq.Scope("power")
```

これだけで veriq の Scope が作られる。
`subsystems/power/analyses.py` の `@analysis` はこの `power` Scope を **自動参照** する（subsystem 自動推論経由）。

### root model 動的構築

`build_subsystem_root_model("power", ...)`:

1. `default_registry.components(subsystem="power")` で全 component 定義を取得
2. 各 component の `plural` をキーに `vq.Table[DynamicEnum, Entry]` field を生やす
3. `DynamicEnum` は **TOML の現在キー** から `load_instance_enum` で動的生成
4. `extra="forbid"` を一律適用

→ **Battery / PDM / SolarPanel を `components.py` に追加するだけで root model が自動拡張される**。本ファイルの修正は不要。

### project への登録

`subsystems/__init__.py` 側で:

```python
import veriq as vq

from .power.verification import power
from .thermal.verification import thermal
from .com.verification import com

project = vq.Project("SpacecraftDesign")
project.add_scope(power)
project.add_scope(thermal)
project.add_scope(com)
```

→ project 統合は **subsystems パッケージの `__init__.py` が担当**。

---

## 新サブシステム追加時の手順

```bash
# 1. ディレクトリを 1 つ作る
mkdir subsystems/aocs
touch subsystems/aocs/{__init__,components,analyses,scope}.py
touch subsystems/aocs/data.toml

# 2. scope.py の中身を↑のテンプレートからコピペ、"power" を "aocs" に置換

# 3. subsystems/__init__.py に追加
#    from .aocs.scope import aocs
#    project.add_scope(aocs)
```

→ **触るファイルは 3 つ**。新サブシステムが即 API/CLI/MCP/Swagger に露出する。

---

## やってはいけないこと

- ❌ `from __future__ import annotations`
- ❌ `@power.calculation` / `@power.verification` を **直接** 書く（必ず `@analysis` 経由）
- ❌ root model に手で field を追加（registry 経由で自動生成すべき）
- ❌ Scope 名と subsystem 名が一致しない（自動推論が壊れる）
