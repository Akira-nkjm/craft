---
tags: [project, dev, satellite, template, code]
mirror: subsystems/cdh/components.py
---

# subsystems/cdh/components.py

> 親: [[実装テンプレート/README|実装テンプレート]]
> 関連: [[インスタンス多重度]] / [[Config設計]]

Command & Data Handling。**default の Singleton** で 1 機構成（OBC）。`MultiInstance` を付けないだけ。

---

## ファイル全体

```python
"""C&DH subsystem components."""

from craft.schema import Component, fld
from craft.schema.traits import (
    PowerConsuming,
    TemperatureSensitive,
)


class OBC(Component, PowerConsuming, TemperatureSensitive):
    """On-Board Computer。本機の中心計算機、1 機構成（default = Singleton）。"""

    clock_mhz: int = fld(ge=0, unit="MHz")
    ram_mb: int = fld(ge=0, unit="MB")
    storage_gb: float = fld(ge=0, unit="GB")
    architecture: str = fld(desc="CPU アーキ (ARM/RISC-V 等)")

    class Design:
        firmware_version: str = fld(default="")
        boot_partition_count: int = fld(ge=1, default=2)

    class Requirements:
        mtbf_hours: float = fld(ge=0, default=50000, unit="h")
        radiation_tolerance_krad: float = fld(ge=0, default=20, unit="krad")
```

---

## 解説

### Singleton (default)

```python
class OBC(Component, ...):    # MultiInstance を付けない = Singleton
    ...
```

- TOML が **flat 構造**（インスタンスキー無し）になる
- registry の `cardinality = "singleton"`（default）
- API path は `/components/cdh/obc`（末尾の `{instance_name}` が消える）
- 既存があるところに POST すると **409 Conflict**
- DELETE は「リセット」（値を空にするが型登録は残す）

### 配置順序

```
Component, PowerConsuming, TemperatureSensitive
    ↑              ↑                  ↑
 必ず最左       field 追加         field 追加
```

`Component` は必ず最左、その他の trait の順序は意味なし（MRO で `__init_subclass__` が `__mro__` 走査）。複数積みたい時は `Component, MultiInstance, ...` の順で `MultiInstance` を 2 番目に。

### `class Design:` を持つ Singleton

Singleton でも `Spec / Design / Requirements` 概念は維持。
**「hardware の properties / engineering choices / must-satisfy constraints」** の 3 層は OBC でも意味がある。

→ **Config と違う点**: Config はこの 3 層を持たない（[[Config設計]] §1 参照）。

### TOML の見え方

```toml
[obc.spec]                  # ← flat、`.main` 等のキーなし
clock_mhz = 100
ram_mb = 512
storage_gb = 32
architecture = "ARM Cortex-R5"
default_power_consumption_per_unit_w = 3.5
operating_temperature_min_c = -40
operating_temperature_max_c = 85

[obc.design]
firmware_version = "v1.2.0"
boot_partition_count = 2

[obc.requirements]
mtbf_hours = 50000
radiation_tolerance_krad = 30

[obc.meta]
vendor = "Aitech"
heritage = "S950-XR"
notes = "JAXA 採用実績あり、放射線対策強化版"
```

---

## CLI

```bash
craft get cdh obc                       # インスタンスキー無し
craft set cdh obc --data '{...}'
craft patch cdh obc --set spec.clock_mhz=120
craft delete cdh obc                    # リセット (= 値クリア、型は残る)
```

---

## いつ Singleton から Multi-instance に migrate するか

「OBC を redundancy で 2 機にする」と決まった瞬間:
1. `MultiInstance` trait を追加（`class OBC(Component, MultiInstance, ...)`）
2. Multi-instance になり TOML が `[obcs.main.spec]` 構造に変わる → migration 必要
3. `craft migrate singleton-to-multi cdh obc --as=main` で既存値を `main` インスタンスに昇格
4. その後 `craft create cdh obc --name=backup --data=...` で 2 機目追加

→ Migration script は [[対処方針]] §A.4 (schema migration) の枠組みで実装。
