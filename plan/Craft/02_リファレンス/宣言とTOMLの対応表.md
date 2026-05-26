---
project: "Craft"
tags: [project, dev, satellite, reference]
date_updated: 2026-05-22
---

# 宣言と TOML の対応表 — 早見リファレンス

> 親: [[Craft]]
> 関連: [[Config設計]] / [[インスタンス多重度]] / [[実装テンプレート/_internals/trait一覧]]

「こう書いたら TOML はこう見える」を 1 ノートに集約した早見表。

---

## 0. 全体マトリクス

> ⚠️ **2026-05-26 方針変更**: `class X(Component):` の **default は Singleton**。
> 複数積む場合は `MultiInstance` trait を明示する（[[インスタンス多重度]]）。
> 旧 P1 (Multi default) → 新 P3 / 旧 P5 (Singleton) → 新 P1 に再ナンバリング。

3 軸の組み合わせと **パターン番号** の対応:

| パターン | kind | cardinality | spec の住み場所 | 代表例 |
|---|---|---|---|---|
| **P1** | Component | **Singleton (default)** | `[name.spec]` flat | OBC, BusStructure |
| **P2** | Component | Singleton | `[name.spec]` flat (SpecOnly) | BusStructure (Design なし) |
| **P3** | Component | Multi | `[plural.spec]` 共有 (`MultiInstance`、default `shared_spec=True`) | Battery, SolarPanel |
| **P4** | Component | Multi | `[plural.spec]` 共有 + traits | PDM (PowerConsuming) |
| **P5** | Component | Multi | `[plural.<name>.spec]` 個別 (`MultiInstance, shared_spec=False`) | Camera (異種製品の併用) |
| **P6** | Component | Multi | `[plural.<name>.spec]` 個別 (`MultiInstance, SpecOnly`) | PanelSurface (material library) |
| **P7** | **Config** | (常 Singleton) | `[name]` フラット | MissionProfile |
| **P8** | Config | (常 Singleton) | 同上 (複数) | 複数 Config 同一ファイル |
| **P9** | Analysis | (関数) | (TOML 無関係) | total_power_by_mode |

---

## P3. Component (Multi, default = shared_spec) — `MultiInstance`

### Python

```python
# systems/power/components.py
from craft.schema import Component, MultiInstance, fld


class Battery(Component, MultiInstance):
    """MultiInstance trait で複数積み宣言、default で全 instance が同じ spec を共有。"""

    capacity_wh: float = fld(ge=0, unit="Wh")

    class Design:
        depth_of_discharge: float = fld(ge=0, le=1)
```

### 自動生成

- `Battery.Spec` (`capacity_wh`)
- `Battery.Design` (`depth_of_discharge`)
- `Battery.Requirements` = None
- `Battery.Entry`
- `Battery.__system__ = "power"` (自動推論)
- `Battery.__plural__ = "batteries"` (自動推論)
- `Battery.__shared_spec__ = True` (default)

### TOML

```toml
[batteries.spec]                  # ← 1 つだけ、全 instance 共有
capacity_wh = 100.0

[batteries.main]                  # ← instance ヘッダ
[batteries.main.design]
depth_of_discharge = 0.7

[batteries.aux]
[batteries.aux.design]
depth_of_discharge = 0.6
```

### API

```
GET /api/components/power/battery          # spec + instance 一覧
GET /api/components/power/battery/main     # 単一 instance (resolved spec 付き)
```

---

## P4. Component (Multi, default + traits)

### Python

```python
class PDM(Component, MultiInstance, PowerConsuming, TemperatureSensitive):
    """PowerConsuming → 自動的に power_modes を持つ。"""

    rated_current_a: float = fld(ge=0, unit="A")
    manufacturer: str = fld(default="")

    class Design:
        efficiency: float = fld(ge=0, le=1, default=0.95)

    class Requirements:
        max_load_a: float = fld(ge=0, unit="A", default=10.0)
```

### Spec / Design 構造

Spec (本体 + trait):
- `rated_current_a, manufacturer` (本体)
- `default_power_consumption_per_unit_w` (PowerConsuming)
- `operating_temperature_min_c, _max_c` (TemperatureSensitive)

Design (本体 + trait):
- `efficiency` (本体)
- `power_modes: dict[OperationMode, bool]` (PowerConsuming)

### TOML

```toml
[pdms.spec]                            # 共有 spec
rated_current_a = 5.0
manufacturer = "Vendor X"
default_power_consumption_per_unit_w = 8.0
operating_temperature_min_c = -30
operating_temperature_max_c = 70

[pdms.main]
[pdms.main.design]
efficiency = 0.95
[pdms.main.design.power_modes]          # ← PowerConsuming 由来
safe = true
nominal = true
science = true
[pdms.main.requirements]
max_load_a = 10.0
[pdms.main.meta]
notes = "primary PDM"

[pdms.backup]
[pdms.backup.design]
efficiency = 0.93
[pdms.backup.design.power_modes]
safe = true
nominal = false                         # backup は通常 off
science = false
[pdms.backup.requirements]
max_load_a = 8.0
```

---

## P5. Component (Multi, `shared_spec=False`)

### Python

```python
class Camera(Component, MultiInstance, PowerConsuming, TemperatureSensitive,
             shared_spec=False):
    """異種カメラを併用するため、instance ごとに別 spec。"""

    sensor_size_mm: float = fld(ge=0, unit="mm")
    resolution_px: int = fld(ge=0)
    manufacturer: str = fld(default="")

    class Design:
        mount_orientation: str = fld()
        position: str = fld()
```

### TOML

```toml
[cameras.visible_wide]
[cameras.visible_wide.spec]            # ← 個別 spec
sensor_size_mm = 23.5
resolution_px = 24000000
manufacturer = "Sony"
default_power_consumption_per_unit_w = 5.0
operating_temperature_min_c = -20
operating_temperature_max_c = 50

[cameras.visible_wide.design]
mount_orientation = "+X"
position = "front_top"
[cameras.visible_wide.design.power_modes]
safe = false
science = true

[cameras.thermal_narrow]
[cameras.thermal_narrow.spec]          # ← 異なる製品
sensor_size_mm = 17.0
resolution_px = 640000
manufacturer = "FLIR"
default_power_consumption_per_unit_w = 8.0
operating_temperature_min_c = -40
operating_temperature_max_c = 60

[cameras.thermal_narrow.design]
mount_orientation = "-X"
position = "rear_top"
[cameras.thermal_narrow.design.power_modes]
safe = false
science = true
```

### いつ `shared_spec=False` を使うか

- **異なる製品** を同 component type で混在 (Sony と FLIR のカメラ等)
- 個体差が大きい (試作品など)

→ 大半の hardware は default (`shared_spec=True`) で OK。

---

## P6. Component (Multi, SpecOnly) — material library

### Python

```python
class PanelSurface(Component, MultiInstance, SpecOnly):
    """Design 概念なし、各 instance が独自の material spec。

    SpecOnly trait は `shared_spec=False` を強制する
    （全 material が同じ properties なら instance を分ける意味がない）。
    """

    emissivity: float = fld(ge=0, le=1)
    absorptivity: float = fld(ge=0, le=1)
    surface_treatment: str = fld(default="")
```

### 自動生成

- `PanelSurface.Spec`
- `PanelSurface.Design` = None (SpecOnly 効果)
- `PanelSurface.Entry`
- `__shared_spec__ = False` (SpecOnly が強制)

### TOML

```toml
[panel_surfaces.white_paint]
[panel_surfaces.white_paint.spec]
emissivity = 0.9
absorptivity = 0.2
surface_treatment = "白塗装"
# [.design] テーブルは出ない (SpecOnly)

[panel_surfaces.mli]
[panel_surfaces.mli.spec]
emissivity = 0.05
absorptivity = 0.05
surface_treatment = "MLI 多層断熱"

[panel_surfaces.black_anodize]
[panel_surfaces.black_anodize.spec]
emissivity = 0.85
absorptivity = 0.95
surface_treatment = "黒色アルマイト"
```

→ 他 component から `vq.Ref("$.panel_surfaces")` で参照される material library として機能。

---

## P1. Component (Singleton, default) — hardware が 1 機

### Python

```python
class OBC(Component, PowerConsuming, TemperatureSensitive):
    """On-Board Computer。default で Singleton（1 機）。MultiInstance を付けないだけ。"""

    clock_mhz: int = fld(ge=0, unit="MHz")
    ram_mb: int = fld(ge=0, unit="MB")
    storage_gb: float = fld(ge=0, unit="GB")
    architecture: str = fld()

    class Design:
        firmware_version: str = fld(default="")
        boot_partition_count: int = fld(ge=1, default=2)

    class Requirements:
        mtbf_hours: float = fld(ge=0, default=50000, unit="h")
        radiation_tolerance_krad: float = fld(ge=0, default=20, unit="krad")
```

### 自動生成

- `__cardinality__ = "singleton"` (default、`MultiInstance` 未継承)
- `__shared_spec__` は **無視** (1 個しかないため moot)
- TOML キー: plural なし、instance キーなし

### TOML

```toml
[obc.spec]                              # ← flat
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
[obc.design.power_modes]               # ← PowerConsuming 由来
safe = true
nominal = true
science = true
safe_hold = true                       # OBC は全 mode で on

[obc.requirements]
mtbf_hours = 50000
radiation_tolerance_krad = 30

[obc.meta]
vendor = "Aitech"
heritage = "S950-XR"
```

### API

```
GET /api/components/cdh/obc            # インスタンスキー無し
```

---

## P2. Component (Singleton + SpecOnly) — 構造体

### Python

```python
class BusStructure(Component, SpecOnly):
    """バス構造本体。1 つしかなく Design 概念もない。"""

    mass_kg: float = fld(ge=0, unit="kg")
    dimensions_mm: str = fld(desc="LxWxH (mm)")
    material: str = fld()
```

### TOML

```toml
[bus_structure.spec]                    # ← flat、Design なし
mass_kg = 12.5
dimensions_mm = "300x200x100"
material = "Al-7075"

[bus_structure.meta]
manufactured_by = "ABC Industries"
serial = "BS-2026-001"
```

---

## P7. Config (シングル)

### Python

```python
# systems/mission/configs.py
from craft.schema import Config, fld


class MissionProfile(Config):
    duration_years: float = fld(ge=0, unit="year")
    target_altitude_km: float = fld(ge=0, unit="km")
    primary_payload: str = fld()
    contact_frequency_per_day: int = fld(ge=0)
```

### 特徴

- 常に Singleton (trait 不要)
- Spec / Design / Requirements の layer **なし**
- フラットな field 群のみ

### TOML

```toml
[mission_profile]                       # ← layer もインスタンスキーもなし
duration_years = 5
target_altitude_km = 600
primary_payload = "imager"
contact_frequency_per_day = 4

[mission_profile.meta]
revision = "v3.2"
approved_by = "akira"
```

### API

```
GET /api/configs/mission/mission_profile    # ← /configs/ プレフィクス
```

---

## P8. Config (同一ファイルに複数)

### Python

```python
class MissionProfile(Config):
    duration_years: float = fld(ge=0, unit="year")
    target_altitude_km: float = fld(ge=0, unit="km")


class OrbitalParameters(Config):
    semi_major_axis_km: float = fld(ge=0, unit="km")
    eccentricity: float = fld(ge=0, lt=1)
    inclination_deg: float = fld(ge=0, le=180, unit="deg")
    raan_deg: float = fld(ge=0, lt=360, unit="deg")


class RadiationEnvironment(Config):
    total_ionizing_dose_krad: float = fld(ge=0, unit="krad")
    single_event_upset_rate_per_day: float = fld(ge=0)
```

### TOML

```toml
[mission_profile]
duration_years = 5
target_altitude_km = 600

[orbital_parameters]
semi_major_axis_km = 6978
eccentricity = 0.001
inclination_deg = 97.6
raan_deg = 45.0

[radiation_environment]
total_ionizing_dose_krad = 30
single_event_upset_rate_per_day = 0.001
```

---

## P9. Analysis (関数)

### Python

```python
# systems/power/analyses.py
from typing import Annotated
import veriq as vq
from craft.schema import analysis
from craft.systems.power.components import Battery, PDM
from craft.schema.common import OperationMode


@analysis(desc="OperationMode 別の総消費電力")
def total_power_by_mode(
    pdms: Annotated[vq.Table[str, PDM.Entry], vq.Ref("$.pdms")],
    mode: OperationMode,
) -> float:
    return sum(
        p.spec.default_power_consumption_per_unit_w        # ← shared spec の値が透過に見える
        for p in pdms.values()
        if p.design.power_modes.get(mode, False)
    )


@analysis(verify=True, desc="バッテリー要求充足")
def verify_battery_capacity(
    batteries: Annotated[vq.Table[str, Battery.Entry], vq.Ref("$.batteries")],
    required_energy_wh: Annotated[float, vq.Ref("@required_battery_energy_wh")],
) -> vq.Table[str, bool]:
    return vq.Table({
        name: b.spec.capacity_wh * b.requirements.depth_of_discharge_max >= required_energy_wh
        for name, b in batteries.items()
    })


@analysis(system=None, desc="バッテリー EOL 容量")
def battery_eol_capacity(
    spec: Annotated[Battery.Entry, vq.Ref("$.batteries.main")],
    years: float = 5.0,
) -> float:
    degradation = min(0.2, 0.0001 * years * 365)
    return spec.spec.capacity_wh * (1.0 - degradation)
```

### TOML

→ **なし**。Analysis は計算関数なので TOML には何も書かない。

### shared_spec 透過性

`shared_spec=True` でも `False` でも、解析関数は `b.spec.capacity_wh` で読める。
（解決済み spec が instance に attach されているため）

### API / CLI

```
POST /api/analyses/power/total_power_by_mode    { "mode": "safe" }
GET  /api/analyses                              # 一覧
GET  /api/analyses/power                        # system 配下
```

---

## 完全な system 例: `systems/power/data.toml`

実際の system の data.toml は混在パターンになる:

```toml
# === Battery (P1/P2: shared spec) ===

[batteries.spec]
capacity_wh = 100.0
nominal_voltage_v = 3.7
manufacturer = "Panasonic"
operating_temperature_min_c = -20
operating_temperature_max_c = 60

[batteries.main]
[batteries.main.design]
depth_of_discharge = 0.7
placement = "primary_bay_port_upper"
[batteries.main.requirements]
depth_of_discharge_max = 0.8

[batteries.aux]
[batteries.aux.design]
depth_of_discharge = 0.6
placement = "primary_bay_port_lower"
[batteries.aux.requirements]
depth_of_discharge_max = 0.8


# === Solar Panel (P1: shared spec) ===

[solar_panels.spec]
area_m2 = 0.5
efficiency = 0.30
cell_type = "IMM"
default_power_generation_per_unit_w = 45
operating_temperature_min_c = -100
operating_temperature_max_c = 120

[solar_panels.port_upper]
[solar_panels.port_upper.design]
mount_angle_deg = 30
position = "port_upper"
cell_count = 32

[solar_panels.port_lower]
[solar_panels.port_lower.design]
mount_angle_deg = -30
position = "port_lower"
cell_count = 32


# === PDM (P2: shared spec + PowerConsuming) ===

[pdms.spec]
rated_current_a = 5.0
default_power_consumption_per_unit_w = 8.0

[pdms.main]
[pdms.main.design]
efficiency = 0.95
[pdms.main.design.power_modes]
safe = true
nominal = true
science = true
safe_hold = false
```

---

## 縮約: 全パターンを 1 表で

| # | 宣言 | TOML キー構造 |
|---|---|---|
| **P1** | `class X(Component):` (default = Singleton) | `[x.spec]` `[x.design]` (flat) |
| **P2** | `class X(Component, SpecOnly):` (Singleton) | `[x.spec]` のみ (flat、Design なし) |
| **P3** | `class X(Component, MultiInstance):` | `[xs.spec]` 共有 + `[xs.<name>.design]` 各 |
| **P4** | `class X(Component, MultiInstance, PowerConsuming, ...):` | 上に加え `[xs.<name>.design.power_modes]` |
| **P5** | `class X(Component, MultiInstance, shared_spec=False):` | `[xs.<name>.spec]` `[xs.<name>.design]` 各 |
| **P6** | `class X(Component, MultiInstance, SpecOnly):` | `[xs.<name>.spec]` のみ (Design なし、shared_spec=False 強制) |
| **P7** | `class X(Config):` | `[x]` 直下に field |
| **P8** | `class X(Config):` x N | トップレベルに複数テーブル |
| **P9** | `@analysis def f(...) -> T:` | TOML 無関係（関数） |

---

## メンタルモデル要約

```
Component の TOML 配置を決めるツリー:

   MultiInstance trait?
   ├── No (= default Singleton)
   │   ├── SpecOnly trait?
   │   │   ├── Yes → [x.spec] のみ (flat) ............... P2
   │   │   └── No  → [x.spec] / [x.design] (flat) ....... P1
   │
   └── Yes (MultiInstance)
       ├── SpecOnly trait?
       │   ├── Yes → 自動的に shared_spec=False
       │   │        [xs.<name>.spec] のみ ................ P6
       │   │
       │   └── No
       │       ├── shared_spec=True (default)
       │       │   [xs.spec] 共有 + [xs.<name>.design] ... P3, P4
       │       │
       │       └── shared_spec=False
       │           [xs.<name>.spec] + [xs.<name>.design] . P5

Config → [x] フラット ............. P7, P8 (常 Singleton)
Analysis → TOML 無関係 ............ P9
```

---

## Trait → TOML 効果

| Trait | TOML 上の効果 |
|---|---|
| (なし) | **default = Singleton**: `[name.spec] / [name.design]` flat、instance キー無し |
| `MultiInstance` | TOML キー singular → plural、`[plural.<instance>...]` の階層追加、`shared_spec` 引数が有効化 |
| `PowerConsuming` | spec に `default_power_consumption_per_unit_w` + design に `power_modes` テーブル |
| `TemperatureSensitive` | spec に `operating_temperature_min_c` / `_max_c` |
| `SpecOnly` | design セクション自動生成スキップ、MultiInstance と併用時は `shared_spec=False` 強制 |

---

## Keyword 引数

| 引数 | デフォルト | 効果 |
|---|---|---|
| `shared_spec` | `True` (MultiInstance のみ有効、Singleton では無視) | `False` で instance ごとに spec を持つ |
| `system` | (ファイル名自動推論) | 明示で上書き |
| `plural` | (クラス名自動推論、MultiInstance のみ有効) | 略語等で明示推奨 |
| `key` | (クラス名 lowercase、Singleton のみ有効) | Singleton 時の TOML キー上書き |

---

## やってはいけない組み合わせ

- ❌ `PowerConsuming` + `SpecOnly` — PowerConsuming は Design に power_modes を要求 → 矛盾
- ❌ Singleton (default、`MultiInstance` なし) + `shared_spec=False` 明示 — 1 個に shared/non-shared は意味なし (warning)
- ❌ `MultiInstance` + `SpecOnly` + `shared_spec=True` 明示 — 同一 spec を持つ instance 複数は無意味 → `TraitConflict`
- ❌ `Config` + 任意の trait — Config は trait を受け付けない（常 Singleton）
- ❌ `Component` を最左にしない `class X(MultiInstance, Component):` — MRO 問題回避のため最左固定
- ❌ 旧 `Singleton` trait — default 化したため不要。書かれていても警告のみ（移行猶予、[[インスタンス多重度]] §11）
