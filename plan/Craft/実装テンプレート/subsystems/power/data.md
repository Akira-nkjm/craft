---
tags: [project, dev, satellite, template, data]
mirror: subsystems/power/data.toml
---

# subsystems/power/data.toml

> 親: [[実装テンプレート/README|実装テンプレート]]
> 関連: [[データパイプライン]] / [[veriq仕様メモ]]

電力サブシステムのインスタンスデータ。通常は API/CLI 経由で更新するが、初期投入や差分確認では直接編集。

**TOML 構造は veriq の `[<Scope>.model.<root_model_field>...]` 規約に準拠**（[[veriq仕様メモ]] §TOML 入出力の構造）。
ここでは `<Scope>` = `power`。

---

## ファイル全体

```toml
# === Batteries (MultiInstance, shared_spec=True default) ===

[power.model.batteries.spec]                # 全 instance 共有の spec
capacity_wh = 100.0
nominal_voltage_v = 3.7
manufacturer = "Panasonic"
operating_temperature_min_c = -20           # TemperatureSensitive trait 由来
operating_temperature_max_c = 60
default_power_consumption_per_unit_w = 0.5  # PowerConsuming trait 由来


[power.model.batteries.main.design]
depth_of_discharge = 0.7

[power.model.batteries.main.design.power_modes]   # PowerConsuming 由来
safe = true
nominal = true
science = true

[power.model.batteries.main.requirements]
depth_of_discharge_max = 0.8

[power.model.batteries.main.meta]            # ← 自由メモ領域、registry 対象外
notes = "選定理由: 過去ミッション実績、価格優位性"
datasheet_url = "https://example.com/datasheet.pdf"
reviewed_by = "akira"
reviewed_date = "2026-05-22"


[power.model.batteries.aux.design]
depth_of_discharge = 0.6

[power.model.batteries.aux.design.power_modes]
safe = true
nominal = false
science = false

[power.model.batteries.aux.requirements]
depth_of_discharge_max = 0.8


# === Solar Panels (MultiInstance) ===

[power.model.solar_panels.spec]
area_m2 = 0.5
efficiency = 0.28
operating_temperature_min_c = -100
operating_temperature_max_c = 120
default_power_generation_per_unit_w = 30   # SolarPanel 直接 field

[power.model.solar_panels.main_paddle.design]
cell_count = 32
string_count = 4


# === PDM (MultiInstance) ===

[power.model.pdms.spec]
rated_current_a = 5.0
default_power_consumption_per_unit_w = 8.0  # PowerConsuming trait 由来

[power.model.pdms.main.design]
efficiency = 0.95

[power.model.pdms.main.design.power_modes]              # HasPowerMode trait 由来
safe = true
nominal = true
science = true
safe_hold = false
```

---

## 解説

### 構造の規約（MultiInstance）

```toml
[<scope>.model.<plural>.spec]                          # shared spec（default）
<spec field 群>

[<scope>.model.<plural>.<instance_name>.design]
<design field 群>

[<scope>.model.<plural>.<instance_name>.requirements] # Requirements 持つ component のみ
<requirement field 群>

[<scope>.model.<plural>.<instance_name>.meta]         # 任意の自由メモ
<key/value 自由>
```

### 構造の規約（Singleton、default）

```toml
[<scope>.model.<name>.spec]              # インスタンスキー無し
<spec field 群>

[<scope>.model.<name>.design]
<design field 群>

[<scope>.model.<name>.requirements]
<requirement field 群>

[<scope>.model.<name>.meta]
```

### `meta` フィールド

- 全 component に **自動付与**（[[実装テンプレート/_internals/Component基底]]）
- 構造制約なし、`extra="forbid"` の対象外
- ⚠️ ここに書いた typo は弾かれない仕様

### trait 由来 field の見え方

| trait | TOML に現れる位置 |
|---|---|
| `PowerConsuming` | `[power.model.<plural>.spec]` に `default_power_consumption_per_unit_w` |
| `TemperatureSensitive` | `[power.model.<plural>.spec]` に `operating_temperature_min_c`, `_max_c` |
| `HasPowerMode` | `[power.model.<plural>.<instance>.design.power_modes]` テーブル |
| `MultiInstance` | `<plural>.<instance_name>` の階層を許可（無い場合は Singleton で `<name>` 直下） |

### veriq による出力（計算 / 検証結果）

`vq.export_to_toml` は **同じ TOML に `.calc.` / `.verification.` セクションを追記**:

```toml
# 入力（このファイル）
[power.model.batteries.spec]
capacity_wh = 100.0

# 出力（result.toml = 入力 + 以下）
[power.calc.total_power_consumption_w]
nominal = 8.5
safe = 0.5

[power.verification.verify_battery_capacity]
passed = true
```

→ `.model.` と `.calc.` / `.verification.` で名前空間が分かれるため、入出力が衝突しない。

---

## 編集経路の使い分け

| 状況 | 推奨手段 |
|---|---|
| 初期データ投入 | `craft scaffold` で雛形生成（[[データパイプライン]] §4） |
| 1〜2 個の追加・変更 | API / CLI |
| 大量バッチ追加 | スクリプトから API を叩く |
| メモ追加 (`meta`) | API / CLI / 手書きどれでも |

---

## やってはいけないこと

- ❌ `[batteries.main]` のような **scope prefix を省略した古い形式**（veriq の `load_model_data_from_toml` が認識しない）
- ❌ Spec の field 名を typo（`capcity_wh` → 起動時 ValidationError）
- ❌ `meta` 以外に未知 field を追加（`extra="forbid"` で弾かれる）
- ❌ コメントを残したい時に Black 等の TOML formatter を当てる（消える可能性）
- ❌ 手で `[power.calc.<...>]` セクションを書く（veriq の出力専用、入力では無視される）
