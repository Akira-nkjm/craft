---
tags: [project, dev, satellite, template, code]
mirror: subsystems/mission/configs.py
---

# subsystems/mission/configs.py

> 親: [[実装テンプレート/README|実装テンプレート]]
> 関連: [[Config設計]]

ミッションレベルの **Config**。`Component` ではなく `Config` 基底クラスを使う。

---

## ファイル全体

```python
"""Mission-level configurations."""

from craft.schema import Config, fld


class MissionProfile(Config):
    """ミッションプロファイル全体。"""

    duration_years: float = fld(ge=0, unit="year", desc="ミッション期間")
    target_altitude_km: float = fld(ge=0, unit="km", desc="目標高度")
    primary_payload: str = fld(desc="主ペイロード種別")
    contact_frequency_per_day: int = fld(ge=0, desc="1 日あたりの地上局可視回数")
    launch_window_start: str = fld(desc="打ち上げ窓開始 (ISO8601)")


class OrbitalParameters(Config):
    """軌道要素（古典 6 元素）。"""

    semi_major_axis_km: float = fld(ge=0, unit="km")
    eccentricity: float = fld(ge=0, lt=1)
    inclination_deg: float = fld(ge=0, le=180, unit="deg")
    raan_deg: float = fld(ge=0, lt=360, unit="deg", desc="昇交点赤経")
    arg_periapsis_deg: float = fld(ge=0, lt=360, unit="deg", desc="近点引数")
    mean_anomaly_deg: float = fld(ge=0, lt=360, unit="deg", desc="平均近点角")
    epoch_utc: str = fld(desc="元期 (ISO8601 UTC)")
```

---

## 解説

### `Config` vs `Component`

| 観点 | `class X(Config)` | `class X(Component)` (default = Singleton) |
|---|---|---|
| 表すもの | 設定値の塊 | hardware（1 機構成） |
| 内部構造 | フラット (field 群のみ) | Spec / Design / Requirements の 3 層 |
| 例 | MissionProfile, OrbitalParameters | OBC, BusStructure |
| TOML 構造 | `[mission_profile]` 直下に field | `[obc.spec]`, `[obc.design]`, `[obc.requirements]` |
| 「設計判断」 layer | 無い | あり (Design class) |

→ **「Design / Requirements を分けて書きたい」**なら Component (default Singleton)、 **「ただの値の集合」**なら Config。

### Config は **常に Singleton**

`MultiInstance` trait は書けない（強制エラー）。Config は **概念上 1 つしか存在しえない**。

### subsystem 自動推論

ファイル `subsystems/mission/configs.py` から `subsystem="mission"` 自動セット。

### TOML の見え方

```toml
[mission_profile]                         # ← 完全にフラット
duration_years = 5
target_altitude_km = 600
primary_payload = "imager"
contact_frequency_per_day = 4
launch_window_start = "2027-04-01T00:00:00Z"

[mission_profile.meta]                    # ← meta はあり
revision = "v3.2"
approved_by = "akira"
last_review_date = "2026-05-22"


[orbital_parameters]
semi_major_axis_km = 6978
eccentricity = 0.001
inclination_deg = 97.6
raan_deg = 45.0
arg_periapsis_deg = 0.0
mean_anomaly_deg = 0.0
epoch_utc = "2027-04-01T00:00:00Z"
```

---

## CLI

```bash
craft config list                          # 全 Config 一覧
craft config get mission profile           # 値取得
craft config set mission profile --data '{...}'
craft config patch mission profile --set duration_years=6
craft config schema mission profile        # JSON Schema
```

→ Config 専用 group。Component の `craft get power battery` とは異なる経路。

---

## API

```http
GET    /api/configs/mission/mission_profile
PUT    /api/configs/mission/mission_profile
PATCH  /api/configs/mission/mission_profile
DELETE /api/configs/mission/mission_profile        # = リセット
GET    /api/configs/mission                        # mission 配下の Config 一覧
GET    /api/configs                                 # 全 Config 一覧（全 subsystem）
```

---

## やってはいけないこと

- ❌ `class MissionProfile(Component):` で書く（Spec/Design/Requirements が無意味になる、Config を使うべき）
- ❌ Config に `class Design:` を書く（実装が無視する）
- ❌ Config に `MultiInstance` trait を書く（強制エラー、Config は常 Singleton）
- ❌ 同一 subsystem に同名 Config を複数（registry 例外）
- ❌ `from __future__ import annotations`
