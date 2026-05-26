---
project: "Craft"
tags: [project, dev, satellite, architecture]
date_updated: 2026-05-22
---

# Datasheet 設計 — 共通スペックの切り出し

> ⚠️ **archive**: `WithDatasheet` trait は採用見送り。
> 「同じ製品を複数積む」ケースは **`class X(Component):` の default (`shared_spec=True`)** で表現する
> （[[宣言とTOMLの対応表]] §P1）。spec が `[plural.spec]` 1 箇所に集約され、instance は design のみ持つ。
> 別テーブル `<plural>_datasheets` への切り出しは追加レイヤとなり、shared_spec で十分なため採用しない。

> 関連: [[インスタンス多重度]] / [[Config設計]] / [[コンポーネントデコレータ仕様]] / [[宣言とTOMLの対応表]]

「同じ製品を複数積むが、配置だけ違う」ケースで spec を **datasheet テーブル** に集約するパターン。
**当時の結論: `WithDatasheet` trait で opt-in、datasheet を別管理**（採用見送り）。

---

## 1. 問題（再掲）

```toml
[batteries.port_upper.spec]
capacity_wh = 100
nominal_voltage_v = 3.7
manufacturer = "Panasonic"

[batteries.port_lower.spec]
capacity_wh = 100        # ← 同じ
nominal_voltage_v = 3.7  # ← 同じ

# starboard_upper / starboard_lower でさらに 2 回繰り返し
```

→ spec が **4 箇所重複**、更新不整合リスク、製品変更で N 箇所修正。

---

## 2. 「Spec が意味なくなる」問題への整理

`WithDatasheet` を導入する時、 **「Instance.spec layer が消えるなら Spec という概念自体が意味ないのでは?」** という懸念。

### 結論: Spec の semantic 意味は変わらない、値が住む場所だけが変わる

| | 値が住む場所 | API/解析の見え方 |
|---|---|---|
| **inline (default)** | 各 instance の `[batteries.main.spec]` | `b.spec.capacity_wh` で読める |
| **`WithDatasheet`** | datasheet テーブル `[battery_datasheets.panasonic_li_2200]` | **同じく** `b.spec.capacity_wh` で読める（自動解決） |

### クラス本体 field 宣言の意味

```python
class Battery(Component, WithDatasheet, TemperatureSensitive):
    capacity_wh: float = fld(ge=0, unit="Wh")   # ← 「Spec の schema」を定義する
    nominal_voltage_v: float = fld(...)
```

これは「Battery の Spec は capacity_wh と nominal_voltage_v を持つ」という **schema 宣言**。
`WithDatasheet` の有無で **schema は不変**、 **値の保存先と書き方** が変わる。

→ **Spec は schema として「製品の intrinsic properties」を意味し続ける**。WithDatasheet では複数 instance が同じ Spec 値を共有するための仕組みが入るだけ。

---

## 3. 名称の整理

`Datasheet` という言葉が 2 つの意味で使われ得るので整理:

| 用語 | 意味 | 対応するもの |
|---|---|---|
| **`SpecOnly` trait** (旧 `Datasheet`) | Component が Design layer を持たない（material library 的） | PanelSurface 等 |
| **`WithDatasheet` trait** (旧 `ProductBased`) | Spec を datasheet テーブルに切り出し、instance は参照のみ | Battery, SolarPanel 等 |
| **datasheet テーブル** (TOML) | `<plural>_datasheets` という固有のテーブル群 | `[battery_datasheets.panasonic_li_2200]` |
| **datasheet entry** | datasheet テーブル内の 1 エントリ | `panasonic_li_2200` |

→ 旧 `Datasheet` trait は **`SpecOnly`** にリネーム（[[実装テンプレート/_internals/trait一覧]]）

---

## 4. `WithDatasheet` trait の使い方

### 4.1 宣言

```python
class Battery(Component, WithDatasheet, TemperatureSensitive):
    """Battery。Spec を datasheet テーブルから引く。"""

    # Spec field (= datasheet entry の schema)
    capacity_wh: float = fld(ge=0, unit="Wh")
    nominal_voltage_v: float = fld(ge=0, unit="V")
    manufacturer: str = fld(default="")

    class Design:
        # インスタンス固有の設計判断
        depth_of_discharge: float = fld(ge=0, le=1)
        placement: str = fld(desc="配置場所")
        thermal_pad_thickness_mm: float = fld(default=2.0, unit="mm")

    class Requirements:
        depth_of_discharge_max: float = fld(default=0.8, gt=0, le=1)
```

### 4.2 TOML 構造

```toml
# === Datasheet テーブル ===
# `<plural>_datasheets` テーブルが自動的に許可される

[battery_datasheets.panasonic_li_2200]
capacity_wh = 100
nominal_voltage_v = 3.7
manufacturer = "Panasonic"
operating_temperature_min_c = -20         # TemperatureSensitive trait 由来
operating_temperature_max_c = 60

[battery_datasheets.panasonic_li_2200.meta]
datasheet_url = "https://..."
heritage = "JAXA missions"


# === Instances ===

[batteries.port_upper]
datasheet = "panasonic_li_2200"           # ← datasheet 参照
[batteries.port_upper.design]
depth_of_discharge = 0.7
placement = "primary_bay_port_upper"
thermal_pad_thickness_mm = 2.5
[batteries.port_upper.requirements]
depth_of_discharge_max = 0.8

[batteries.port_lower]
datasheet = "panasonic_li_2200"           # ← 同じ datasheet 参照
[batteries.port_lower.design]
depth_of_discharge = 0.7
placement = "primary_bay_port_lower"

[batteries.starboard_upper]
datasheet = "panasonic_li_2200"
[batteries.starboard_upper.design]
depth_of_discharge = 0.7
placement = "primary_bay_starboard_upper"

[batteries.starboard_lower]
datasheet = "panasonic_li_2200"
[batteries.starboard_lower.design]
depth_of_discharge = 0.7
placement = "primary_bay_starboard_lower"
```

→ spec は **1 箇所、4 instance は datasheet 参照と placement のみ**。

### 4.3 メモリ上の表現

ロード時に **自動解決**。`@analysis` 内で扱う Entry は **解決済み spec を持つ**:

```python
@analysis
def total_capacity(
    batteries: Annotated[vq.Table[str, Battery.Entry], vq.Ref("$.batteries")],
) -> float:
    # batteries["port_upper"].spec.capacity_wh が普通に使える
    # （内部的には datasheet から resolve 済み）
    return sum(b.spec.capacity_wh for b in batteries.values())
```

→ **解析関数の書き方は変わらない**。datasheet 参照は I/O 層で吸収。**Spec layer は意味を持ち続ける**。

### 4.4 API レスポンス

```http
GET /api/components/power/battery/port_upper

{
  "datasheet": "panasonic_li_2200",
  "spec": {                                    # ← datasheet から resolve 済み
    "capacity_wh": 100,
    "nominal_voltage_v": 3.7,
    "manufacturer": "Panasonic",
    "operating_temperature_min_c": -20,
    "operating_temperature_max_c": 60
  },
  "design": {
    "depth_of_discharge": 0.7,
    "placement": "primary_bay_port_upper",
    "thermal_pad_thickness_mm": 2.5
  },
  "requirements": {
    "depth_of_discharge_max": 0.8
  }
}
```

PUT/PATCH は `datasheet` + `design` + `requirements` のみ受領（`spec` は write 禁止）:

```http
PUT /api/components/power/battery/port_upper
{
  "datasheet": "panasonic_li_2200",
  "design": {...},
  "requirements": {...}
}
```

`spec` を送ると **422** (`"cannot write spec on a WithDatasheet component; modify the datasheet entry instead"`).

---

## 5. Datasheet API

```http
# datasheet 操作
GET    /api/datasheets/power/battery                           # 一覧
GET    /api/datasheets/power/battery/panasonic_li_2200         # 単一
POST   /api/datasheets/power/battery/panasonic_li_2200         # 追加
PUT    /api/datasheets/power/battery/panasonic_li_2200         # 更新
DELETE /api/datasheets/power/battery/panasonic_li_2200         # 削除（使用中なら 409）
```

### 削除時の参照整合性

使用中の datasheet を削除しようとすると **409 Conflict** + 使用 instance 一覧を返す。

### datasheet のバージョニング

datasheet 値の変更は **既存 instance に自動波及**。バージョン管理したい場合:
- datasheet キーに version 埋め込み: `panasonic_li_2200_v1` / `_v2`
- instance は特定 version を参照
- → 設計者責任、framework は強制しない

---

## 6. CLI

```bash
# datasheet 操作
experiment datasheet list power battery
experiment datasheet get power battery panasonic_li_2200
experiment datasheet create power battery panasonic_li_2200 --data '{...}'
experiment datasheet update power battery panasonic_li_2200 --set capacity_wh=110

# instance 操作 (既存)
craft create power battery port_upper \
    --datasheet panasonic_li_2200 \
    --design '{"placement": "...", "depth_of_discharge": 0.7}'
```

---

## 7. 採用判断

### `WithDatasheet` を使うべき component

- **市販品で同型を複数積む** — Battery, SolarPanel, RW, IMU
- **データシートが存在し spec が固定** — Transceiver, Antenna
- **製品比較・選定をしたい** — A 社 vs B 社の比較で spec 差を見やすく

### `WithDatasheet` を使わない方が良い component

- **完全カスタム品** — Bus Structure, Custom Payload
- **1 機しか使わない** — OBC（むしろ Singleton 化）
- **spec が試作中で頻繁に変わる** — 初期段階の暫定 component

### 後付け移行

「Battery を WithDatasheet にしたい」と気付いた時:
1. `WithDatasheet` trait を追加
2. `craft migrate to-datasheet power battery --datasheet-name=auto` で既存 instance の spec を 1 つの datasheet エントリに集約
3. spec 差異がある場合は migration が複数候補を提示 → 人間が選ぶ

---

## 8. veriq との関係

veriq Ref の path には spec の解決済み値が見える:

```python
@analysis
def battery_drain(
    bat: Annotated[Battery.Entry, vq.Ref("$.batteries.port_upper")],
) -> float:
    return bat.spec.capacity_wh * 0.8       # spec は resolved 済みで OK
```

`build_system_root_model` 時に datasheet 参照を resolve してから validate。
→ veriq 側は WithDatasheet を意識しない。透過。

---

## 9. registry / definition への影響

### ComponentDefinition の拡張

```python
@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    ...
    has_datasheet_table: bool                 # WithDatasheet trait の有無
    datasheet_table_key: str | None           # "battery_datasheets" 等
    spec_only: bool                           # SpecOnly trait の有無 (= Design なし)
```

### datasheet 定義は registry には別途登録不要

`WithDatasheet` の component に対しては:
- インスタンス用の `Entry` model
- datasheet 用の `DatasheetSpec` model (= Spec model)
- 同じ ComponentDefinition から両方を派生

---

## 10. Trait 組み合わせ

| 組み合わせ | 挙動 |
|---|---|
| `WithDatasheet` + `Singleton` | ❌ 矛盾。Singleton は 1 個なので datasheet 共有不要 → `TraitConflict` |
| `WithDatasheet` + `SpecOnly` | ✅ Design なしでも spec を datasheet 化したいケース |
| `WithDatasheet` + `HasPowerMode` | ✅ power_modes は Design 側、datasheet と独立 |
| `WithDatasheet` + `TemperatureSensitive` | ✅ temperature 系 field は spec 側で datasheet 入り |
| `WithDatasheet` + `PowerConsuming` | ✅ Spec field は datasheet、Design `power_modes` は instance 側 |

---

## 11. 例: SolarPanel に適用

```python
class SolarPanel(Component, WithDatasheet, TemperatureSensitive):
    area_m2: float = fld(ge=0, unit="m^2")
    efficiency: float = fld(ge=0, le=1)
    cell_type: str = fld(desc="GaAs / Si / IMM 等")
    default_power_generation_per_unit_w: float = fld(ge=0, unit="W")

    class Design:
        mount_angle_deg: float = fld(unit="deg")
        position: str = fld(desc="port_upper / starboard_lower 等")
        cell_count: int = fld(ge=1)
        string_count: int = fld(ge=1)
```

```toml
[solar_panel_datasheets.acme_imm_30]
area_m2 = 0.5
efficiency = 0.30
cell_type = "IMM"
default_power_generation_per_unit_w = 45
operating_temperature_min_c = -100
operating_temperature_max_c = 120

[solar_panels.port_upper]
datasheet = "acme_imm_30"
[solar_panels.port_upper.design]
mount_angle_deg = 30
position = "port_upper"
cell_count = 32
string_count = 4

[solar_panels.port_lower]
datasheet = "acme_imm_30"
[solar_panels.port_lower.design]
mount_angle_deg = -30
position = "port_lower"
cell_count = 32
string_count = 4
```

→ **4 パネルでも spec は 1 箇所**。新製品 (`acme_imm_32`) に切り替えるなら datasheet を更新 + 該当 instance の `datasheet` だけ書き換え。

---

## 12. 確定事項

| 項目 | 決定 |
|---|---|
| パターン | **Datasheet / Instance 分離**、`WithDatasheet` trait で opt-in |
| 旧 `Datasheet` trait | **`SpecOnly` に rename**（Design layer なしの意味） |
| datasheet テーブルの TOML | `<plural>_datasheets` テーブル（自動許可） |
| instance の spec 書き込み | **API は禁止** (422)、TOML は読み込み時にエラー |
| 解析関数からの見え方 | resolved spec が見える、透過 |
| Spec layer の意味 | **schema として存続**、値の保存先だけ変わる |
| API | `/api/datasheets/{sub}/{name}/{datasheet_key}` 系を追加 |
| CLI | `experiment datasheet <verb>` 専用 group |
| Singleton との組み合わせ | ❌ 矛盾、`TraitConflict` |
| 削除時の参照整合性 | 使用中なら 409 Conflict |

---

## 13. 残る論点

- **個体差オーバーライド** — 同型製品でも個体差ある場合 → **不可、別 datasheet エントリ作成** を推奨
- **クロスサブシステム datasheet 共有** — 暫定: **system ごと持つ**（rare case はコピペで運用）
- **datasheet → instance への fallback** — 「とりあえず inline spec で書いて、後で datasheet 化」の動線 → `craft migrate to-datasheet ...`
- **datasheet revision** — `xyz_v1`, `xyz_v2` 等、キー命名で運用、framework 強制せず
