# craft インスタンス操作

インスタンスデータの読み書きを行うコマンド群。ETag による楽観的排他制御を備える。

---

## craft get

### `craft get <system> <component> [<instance>]`

インスタンスを取得する。`<instance>` を省略すると全インスタンスを返す。

```bash
# 全インスタンスを取得
uv run craft get power battery

# 特定インスタンスを取得
uv run craft get power battery main
```

**引数**

| 引数 | 必須 | 説明 |
|---|---|---|
| `system` | はい | 対象の system 名 |
| `component` | はい | 対象の component 名 |
| `instance` | いいえ | 省略時は全件返す |

**出力形式**

先頭行に ETag が出力され、続いて JSON が続く。

```
# ETag: "abc123def456"
{
  "spec": {
    "capacity_wh": 100.0,
    "nominal_voltage_v": 3.7
  },
  "design": {
    "depth_of_discharge": 0.7
  },
  "requirements": {
    "depth_of_discharge_max": 0.8
  },
  "meta": null
}
```

!!! note "ETag の使い方"
    取得した ETag は `put` / `patch` / `delete` の `--etag` に渡す。
    省略した場合はコマンドが自動で GET して取得するが、並列更新がある環境では明示指定を推奨する。

---

## CRUD コマンド

### データ入力の 3 通りの方法

`create` / `put` / `patch` / `spec set` はすべて以下の形式でデータを受け取る。

| 方法 | オプション | 例 |
|---|---|---|
| ファイル指定 | `--data <path>` | `--data ./battery.toml`（TOML / JSON） |
| インライン JSON | `--json <str>` | `--json '{"design": {"depth_of_discharge": 0.7}}'` |
| 標準入力 | なし（自動検出） | `cat battery.json \| craft create ...` |

---

### `craft create <system> <component> <instance>`

新規インスタンスを作成する。**MultiInstance コンポーネントにのみ有効**。

```bash
uv run craft create power battery aux --data ./aux_battery.toml

uv run craft create power battery aux \
  --json '{"design": {"depth_of_discharge": 0.6}}'
```

---

### `craft put <system> <component> <instance>`

既存インスタンスを完全置換する。省略したフィールドはデフォルト値にリセットされる。

```bash
uv run craft put power battery main --data ./main_battery.toml

# ETag を明示指定
uv run craft put power battery main \
  --data ./main_battery.toml \
  --etag '"abc123def456"'
```

**オプション**

| オプション | 説明 |
|---|---|
| `--etag <etag>` | 楽観的排他制御用 ETag。省略時は自動取得 |

---

### `craft patch <system> <component> <instance>`

既存インスタンスを部分更新する。指定したフィールドのみ更新し、他は保持（深いマージ）。

```bash
uv run craft patch power battery main \
  --json '{"design": {"depth_of_discharge": 0.65}}'
```

**オプション**

| オプション | 説明 |
|---|---|
| `--etag <etag>` | 楽観的排他制御用 ETag。省略時は自動取得 |

!!! tip "`put` と `patch` の使い分け"
    - 全フィールドを確定値で上書きしたい → `put`
    - 特定フィールドだけ変えて他は現状維持 → `patch`

---

### `craft delete <system> <component> <instance>`

インスタンスを削除する。

```bash
uv run craft delete power battery old_battery

uv run craft delete power battery old_battery --etag '"abc123def456"'
```

!!! warning "削除は取り消せない"
    重要なインスタンスを削除する前に `craft get` でバックアップを取ること。

---

## craft spec

MultiInstance コンポーネントの **共有 spec** を操作する。

共有 spec は同型の複数インスタンスで `spec` セクションを共通化する仕組み
（例: 同型バッテリ × 3 台が同じ spec を持つ場合）。

### `craft spec get <system> <component>`

共有 spec を取得する。

```bash
uv run craft spec get power battery
```

```
# ETag: "spec_etag_xyz"
{
  "capacity_wh": 100.0,
  "nominal_voltage_v": 3.7,
  "manufacturer": "Panasonic"
}
```

---

### `craft spec set <system> <component>`

共有 spec を更新する。セクション全体を置換する（部分更新は `get` → 編集 → `set`）。

```bash
uv run craft spec set power battery --data ./battery_spec.toml

uv run craft spec set power battery \
  --json '{"capacity_wh": 120.0}' \
  --etag '"spec_etag_xyz"'
```

---

## 付録: ETag による楽観的排他制御

`put` / `patch` / `delete` / `spec set` はすべて ETag で同時更新の競合を検出する。

```
craft get → # ETag: "abc123"
craft put --etag "abc123" → 成功（ETag 一致）
craft put --etag "abc123" → 409 Conflict（別の更新が先行した場合）
```

スクリプトでの明示的な ETag 取得例：

```bash
ETAG=$(uv run craft get power battery main | head -1 | awk '{print $3}')
uv run craft patch power battery main \
  --json '{"design": {"depth_of_discharge": 0.65}}' \
  --etag "$ETAG"
```
