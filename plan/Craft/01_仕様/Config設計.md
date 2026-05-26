---
project: "Craft"
tags: [project, dev, satellite, architecture]
date_updated: 2026-05-22
---

# Config 設計 — 非 hardware パラメータの扱い

> 親: [[最終構成]] / 関連: [[インスタンス多重度]] / [[UnifiedRegistry設計]] / [[コンポーネントデコレータ仕様]]

`Component` とは別概念として **`Config`** を導入。
ミッション要求・軌道・環境定義などの **「物体ではない設定値の塊」** を表現する。

---

## 1. なぜ別概念にするか

### Component とは違うもの

| 観点 | Component | Config |
|---|---|---|
| 表すもの | 物理的なハードウェア | 設定値・運用条件・要求 |
| 例 | Battery, OBC, Antenna | MissionProfile, OrbitalParameters, RadiationEnvironment |
| サブ構造 | Spec / Design / Requirements の **3 層** | フラットな field 群 |
| 「設計判断」 | Design layer で持つ | 概念として無い（値そのものが設計判断） |
| 多重度 | default Singleton、`MultiInstance` で opt-in | **常に Singleton**（`MultiInstance` 不可） |
| 物理単位 | 個数で数えられる | 個数概念がない |

### Config を Component で表現しようとすると

```python
class MissionProfile(Component):     # default Singleton
    duration_years: float = fld(...)

    class Design:          # ← 何を書く?
        pass

    class Requirements:    # ← 何を書く?
        pass
```

→ Spec / Design / Requirements が空 or 重複してしまう。 **モデル構造の表現力が無駄になる**。

→ 別 base class が妥当。

---

## 2. `Config` base class の使い方

```python
# systems/mission/configs.py

from craft.schema import Config, fld


class MissionProfile(Config):
    """ミッションプロファイル。常に 1 つ。"""

    duration_years: float = fld(ge=0, unit="year")
    target_altitude_km: float = fld(ge=0, unit="km")
    primary_payload: str = fld(desc="主ペイロードの種別")
    launch_window_start: str = fld(desc="打ち上げ窓開始 (ISO8601)")


class OrbitalParameters(Config):
    """軌道要素。"""

    semi_major_axis_km: float = fld(ge=0, unit="km")
    eccentricity: float = fld(ge=0, lt=1)
    inclination_deg: float = fld(ge=0, le=180, unit="deg")
    raan_deg: float = fld(ge=0, lt=360, unit="deg")
    arg_periapsis_deg: float = fld(ge=0, lt=360, unit="deg")
    mean_anomaly_deg: float = fld(ge=0, lt=360, unit="deg")
```

### system 自動推論

ファイルパス `systems/mission/configs.py` から `system="mission"` を自動推論。Component と同じロジック。

### Singleton が default（強制）

`Config` は **概念上 Singleton 確定**。`MultiInstance` trait は付けられない（強制エラー）。
Component の default Singleton と同じ TOML フラット構造になるが、内部 3 層（Spec/Design/Requirements）を持たない点が異なる。

---

## 3. TOML 構造

Component (default = Singleton, hardware OBC):
```toml
[obc.spec]
clock_mhz = 100
[obc.design]
voltage_level_v = 3.3
[obc.requirements]
mtbf_hours = 50000
```

Component (MultiInstance):
```toml
[batteries.spec]                # shared_spec=True (default)
capacity_wh = 100
[batteries.main.design]
depth_of_discharge = 0.7
```

Config (常に Singleton, layer 無し):
```toml
[mission_profile]
duration_years = 5
target_altitude_km = 600
primary_payload = "imager"
launch_window_start = "2027-04-01T00:00:00Z"

[orbital_parameters]
semi_major_axis_km = 6978
eccentricity = 0.001
inclination_deg = 97.6
# ...
```

→ Config の TOML 構造が **最もフラット**。設定ファイルとして読みやすい。

### `meta` フィールド

Config にも `meta` テーブル自動付与:
```toml
[mission_profile]
duration_years = 5

[mission_profile.meta]
revision = "v3.2"
approved_by = "akira"
```

---

## 4. registry / API への影響

### UnifiedRegistry の拡張

```python
class UnifiedRegistry:
    components: dict[(str, str), ComponentDefinition]   # (system, name)
    configs:    dict[(str, str), ConfigDefinition]      # (system, name)
    analyses:   dict[(str|None, str), AnalysisDefinition]

    def register_config(self, defn: ConfigDefinition) -> None: ...
    def config(self, system: str, name: str) -> ConfigDefinition: ...
    def configs(self, *, system: str | None = None) -> list[ConfigDefinition]: ...
```

### ConfigDefinition

```python
@dataclass(frozen=True, slots=True)
class ConfigDefinition:
    system: str
    name: str                          # "mission_profile"
    model: type[BaseModel]             # MissionProfile 自身
    desc: str | None
    tags: tuple[str, ...]
    source: SourceLocation
```

Component の `spec` / `design` / `requirements` / `entry` は無く、 **`model` 1 つだけ**。

### API endpoint

| 操作 | Component | Config |
|---|---|---|
| 取得 | `GET /api/components/power/battery/main` | `GET /api/configs/mission/mission_profile` |
| 一覧 | `GET /api/components/power/battery` | `GET /api/configs/mission` |
| 更新 | `PUT /api/components/power/battery/main` | `PUT /api/configs/mission/mission_profile` |
| 削除 | `DELETE /api/components/power/battery/main` | `DELETE /api/configs/mission/mission_profile` (= リセット) |
| Schema | `GET /api/schema/power/battery` | `GET /api/configs/mission/mission_profile/schema` |

---

## 5. veriq との関係

Config も veriq の `Scope` に乗る。`@analysis` から `vq.Ref` で参照可能:

```python
@analysis
def required_battery_energy_wh(
    profile: Annotated[MissionProfile, vq.Ref("$.mission_profile", scope="mission")],
    eclipse_s: Annotated[float, vq.Ref("@calc_eclipse_s", scope="orbital")],
) -> float:
    return ... * profile.duration_years * eclipse_s / 3600
```

→ Config は veriq の root model に **直接 field として** 入る（Table 経由ではない）。
```python
class MissionRootModel(BaseModel):
    mission_profile: MissionProfile     # ← Singleton なので直接
    # batteries: vq.Table[..., Battery.Entry]    # ← Multi-instance はこちら
```

---

## 6. ディレクトリ配置

### system-centric を踏襲

```
systems/
├── power/                # hardware 主体
│   ├── components.py     # Battery, SolarPanel, PDM
│   ├── analyses.py
│   ├── scope.py
│   └── data.toml
│
├── mission/              # 非 hardware 主体
│   ├── configs.py        # MissionProfile, OrbitalParameters (system 名は "mission")
│   ├── analyses.py       # ミッション系の集計関数
│   ├── scope.py
│   └── data.toml
│
├── environment/
│   ├── configs.py        # RadiationEnvironment, ThermalEnvironment
│   ├── scope.py
│   └── data.toml
│
└── cdh/                  # OBC など hardware singleton 系
    ├── components.py     # class OBC(Component): ... （default Singleton）
    ├── analyses.py
    ├── scope.py
    └── data.toml
```

### ファイル分け

- **`components.py`** — `Component` 派生
- **`configs.py`** — `Config` 派生
- **`analyses.py`** — `@analysis` 関数
- **`scope.py`** — veriq Scope 定義
- **`data.toml`** — インスタンス + Config 値

Component と Config の **両方を持つ system** もあり得る（例: power に `EPSConfig` を足す）。その場合は両ファイルを置く。

---

## 7. 4 つの基本パターンまとめ

| 概念 | base | cardinality | TOML 構造 | 例 |
|---|---|---|---|---|
| Component (Singleton, **default**) | `Component` | Singleton | `[<name>.spec]` flat | OBC, BusStructure |
| Component (MultiInstance) | `Component, MultiInstance` | Multi | `[<plural>.<name>.spec]` | Battery, SolarPanel |
| Config | `Config` | 常に Singleton | `[<name>]` (フラット、3 層なし) | MissionProfile |
| Analysis (関数) | `@analysis` | (関数) | (TOML に乗らない) | total_power_by_mode |

---

## 8. 例: `systems/cdh/components.py`

```python
"""Command & Data Handling system."""

from craft.schema import Component, fld
from craft.schema.traits import (
    PowerConsuming,
    TemperatureSensitive,
)


class OBC(Component, PowerConsuming, TemperatureSensitive):
    """On-Board Computer。default Singleton。冗長は将来必要なら MultiInstance に migration。"""

    clock_mhz: int = fld(ge=0, unit="MHz")
    ram_mb: int = fld(ge=0, unit="MB")
    storage_gb: float = fld(ge=0, unit="GB")
    architecture: str = fld(desc="CPU アーキ (ARM/RISC-V 等)")

    class Design:
        firmware_version: str = fld()
        boot_partition_count: int = fld(ge=1, default=2)

    class Requirements:
        mtbf_hours: float = fld(ge=0, default=50000, unit="h")
        radiation_tolerance_krad: float = fld(ge=0, default=20, unit="krad")
```

TOML:
```toml
[obc.spec]
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
```

---

## 9. 例: `systems/mission/configs.py`

```python
"""Mission-level configurations."""

from craft.schema import Config, fld


class MissionProfile(Config):
    duration_years: float = fld(ge=0, unit="year")
    target_altitude_km: float = fld(ge=0, unit="km")
    primary_payload: str = fld()
    contact_frequency_per_day: int = fld(ge=0)


class OrbitalParameters(Config):
    semi_major_axis_km: float = fld(ge=0, unit="km")
    eccentricity: float = fld(ge=0, lt=1)
    inclination_deg: float = fld(ge=0, le=180, unit="deg")
    # ...
```

TOML:
```toml
[mission_profile]
duration_years = 5
target_altitude_km = 600
primary_payload = "imager"
contact_frequency_per_day = 4

[orbital_parameters]
semi_major_axis_km = 6978
eccentricity = 0.001
inclination_deg = 97.6
```

---

## 10. CLI への影響

```bash
# Component (Singleton, default)
craft get cdh obc                     # インスタンスキー無し
craft set cdh obc --data '{...}'

# Component (MultiInstance)
craft get power battery
craft get power battery main
craft set power battery aux --data '{...}'

# Config
craft config get mission profile      # 専用 "config" group
craft config set mission profile --data '{...}'
craft config list                     # 全 Config 一覧
```

→ Config は **専用 CLI group** で操作。Component と混ざらない。

---

## 11. MCP / Swagger への影響

- Swagger UI で `Components` と `Configs` のタブを分ける
- MCP の tools: `add_<component>` / `set_<config>` で命名分離
- `tools/list` で「Component 系 / Config 系」の tag を分ける

---

## 12. 確定事項

| 項目 | 決定 |
|---|---|
| Config 概念 | ✅ 別 base class として導入 |
| Config の cardinality | **常に Singleton**（trait 不要） |
| Config の構造 | フラット (Spec/Design/Requirements 無し) |
| Config の system 帰属 | ファイルパスから自動推論 |
| TOML 配置 | system の `data.toml` に同居 |
| API endpoint prefix | `/api/configs/{system}/{name}` |
| CLI group | `craft config <verb> ...` |
| veriq 連携 | root model に直接 field として含まれる |
| `meta` フィールド | あり |

---

## 13. 残る論点

- **Config と Component を同 system 内に混在** させる時の TOML 階層 — 同じ `data.toml` でいいか別ファイルがいいか
- **Config に `Requirements` 概念は本当に不要か** — 「ミッション要求」は要求の塊なので、別構造が要らない理由を明確化
  - → MissionProfile 自体が「要求の宣言」、別の Requirements layer は不要、と整理
- **`Config` に trait は適用可能か** — `meta` 以外で意味のある trait があるか（多分なし、`MultiInstance` は禁止）
- **Config の variant** — 「ミッション A 向け / ミッション B 向け」を切り替えたい時、複数 Config を同名で持てるか
  - → ❌ 同名 Config 重複不可。バリアントは別ファイル or `Multi-instance Config` を将来導入で対処
