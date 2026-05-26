---
tags: [project, dev, satellite, template, data]
mirror: design/data/system/power.toml
---

# design/data/system/power.toml

> 親: [[実装テンプレート/README|実装テンプレート]]

インスタンスデータ。**通常は API/CLI 経由で更新**するが、初期投入や差分確認で直接編集することも。

---

## ファイル全体

```toml
# === Batteries ===

[batteries.main]
[batteries.main.spec]
capacity_wh = 100.0
nominal_voltage_v = 3.7
manufacturer = "Panasonic"
operating_temperature_min_c = -20      # mixin="temperature" 由来
operating_temperature_max_c = 60

[batteries.main.design]
depth_of_discharge = 0.7

[batteries.main.requirements]
depth_of_discharge_max = 0.8

[batteries.main.meta]                  # ← 自由メモ領域、registry の対象外
notes = "選定理由: 過去ミッション実績、価格優位性"
datasheet_url = "https://example.com/datasheet.pdf"
reviewed_by = "akira"
reviewed_date = "2026-05-22"


[batteries.aux]
[batteries.aux.spec]
capacity_wh = 50.0
nominal_voltage_v = 3.7
operating_temperature_min_c = -20
operating_temperature_max_c = 60

[batteries.aux.design]
depth_of_discharge = 0.6

[batteries.aux.requirements]
depth_of_discharge_max = 0.8


# === Solar Panels ===

[solar_panels.main_paddle]
[solar_panels.main_paddle.spec]
area_m2 = 0.5
efficiency = 0.28
operating_temperature_min_c = -100
operating_temperature_max_c = 120
default_power_consumption_per_unit_w = 0    # base="power_spec" 由来（発電側は 0）

[solar_panels.main_paddle.design]
cell_count = 32
string_count = 4


# === PDM ===

[pdms.main]
[pdms.main.spec]
rated_current_a = 5.0
default_power_consumption_per_unit_w = 8.0

[pdms.main.design]
efficiency = 0.95

[pdms.main.design.power_modes]         # ← has_power_mode=True 由来
safe = true
nominal = true
science = true
safe_hold = false
```

---

## 解説

### 構造の規約

```toml
[<plural>.<instance_name>]              # ← Entry のヘッダ（中身は空でも書く）

[<plural>.<instance_name>.spec]
<spec の field 群>

[<plural>.<instance_name>.design]
<design の field 群>

[<plural>.<instance_name>.requirements] # Requirements がある component のみ
<requirement の field 群>

[<plural>.<instance_name>.meta]         # 任意。自由メモ
<どんな key/value でも OK>
```

### `meta` フィールド

- 全 component に **自動付与**（[[コンポーネントデコレータ仕様]] §meta フィールド）
- registry の対象外なので **典型外の情報** をここに置く
- 例:
  - `notes` — 選定理由・補足説明
  - `datasheet_url` — データシート URL
  - `reviewed_by` / `reviewed_date` — レビュー履歴
  - `tags` — 自由タグ
- ⚠️ ここに書いた typo は弾かれない仕様

### `has_power_mode=True` の TOML

```toml
[pdms.main.design.power_modes]
safe = true
nominal = true
science = true
```

各 `OperationMode` enum 値に対する on/off。書いていないモードは `false` 扱い。

---

## 手で TOML を書くべきか

| 状況 | 推奨手段 |
|---|---|
| 初期データ投入 | 手書き or `craft init` で雛形生成 |
| 1〜2 個の追加 | API / CLI |
| 大量バッチ追加 | スクリプトで API を叩く |
| 値の微調整 | API / CLI |
| メモ追加 | 手書き（meta 内なら自由） |

→ 基本は **API / CLI に寄せる**。手書きは初期化・緊急時のみ。

---

## やってはいけないこと

- ❌ `[batteries.main]` と書かずに直接 `[batteries.main.spec]` から始める（registry は entry header を期待）
- ❌ Spec の field 名を typo する（`capcity_wh` → 起動時に `ValidationError`）
- ❌ `meta` 以外の場所に未知 field を追加（`extra="forbid"` に弾かれる）
- ❌ TOML をエディタで手書き後、整形ツール（Black 等）にかける（コメントが消える可能性）
