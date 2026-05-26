# craft パイプライン

`data.toml` から veriq 検証までの処理フローを操作するコマンド群。

```
data.toml → merge → merged.toml → verify → 検証結果 → runs
```

---

## craft merge

各 system の `data.toml` を結合して `generated/merged.toml` を生成する。

### `craft merge [--dry-run] [--check]`

```bash
# 通常実行（generated/merged.toml を更新）
uv run craft merge

# ドライラン（stdout に出力、ファイル書き込みなし）
uv run craft merge --dry-run

# CI 用チェック（stale なら exit 1）
uv run craft merge --check
```

**オプション**

| オプション | 説明 |
|---|---|
| `--dry-run` | マージ結果を stdout に出力するだけ。`merged.toml` / `merged.lock` は更新しない |
| `--check` | `merged.lock` が最新かどうかを確認し、stale なら exit 1（CI 用） |

**動作の詳細**

- `systems/<name>/data.toml` を読み込み、veriq 規約（`[<scope>.model.<...>]`）に変換しながら結合する
- `tomlkit` を使用してコメント・空行・順序を保持する
- 出力先: `generated/merged.toml`（ロックファイル: `generated/merged.lock`）

!!! tip "CI での使い方"
    ```yaml
    - name: Check merge is up to date
      run: uv run craft merge --check
    ```

---

## craft scaffold

Registry に登録された Component の定義から `data.toml` の雛形を生成する。**既存の値は保持される**。

### `craft scaffold [<system>] [--dry-run]`

```bash
# すべての system を対象
uv run craft scaffold

# 特定 system のみ
uv run craft scaffold power

# ファイルを変更せず差分を確認
uv run craft scaffold power --dry-run
```

**引数・オプション**

| 引数 / オプション | 説明 |
|---|---|
| `system` | 省略時は全 system |
| `--dry-run` | 変更内容を stdout に出力するだけ |

!!! note "欠けているキーのみ追加する"
    `craft scaffold` は既存の値を上書きしない。新しい Component を追加した後に実行するのが典型的なワークフロー。

**典型的なワークフロー**

```bash
# 1. components.py に新しい Component を追加
# 2. 雛形を生成（差分確認）
uv run craft scaffold power --dry-run
# 3. 確認後に適用
uv run craft scaffold power
# 4. data.toml に値を記入して検証
uv run craft verify
```

---

## craft verify

`data.toml` をマージし、veriq で検証を実行する。

### `craft verify [--async] [--no-fail-on-verify]`

```bash
# 同期実行（検証完了まで待機）
uv run craft verify

# 非同期実行（job_id を表示して即終了）
uv run craft verify --async

# 検証失敗でも exit 0 を返す（エラー内容の確認用）
uv run craft verify --no-fail-on-verify
```

**オプション**

| オプション | 説明 |
|---|---|
| `--async` | veriq ジョブを投入して即座に終了。結果は `craft runs` で確認 |
| `--no-fail-on-verify` | verification 失敗でも exit 1 にしない。merge エラーは引き続き exit 1 |

**出力例**

```
  CALC power/@total_pdm_power_w  =  8.0
  CALC power/@required_orbit_energy_wh  =  0.533
  VERI ✓ power/?verify_battery_capacity  =  True
success=True, errors=0, run_id=20260526_120000_abc
```

!!! tip "非同期実行のユースケース"
    ```bash
    uv run craft verify --async
    # → job_id: 01HXYZ...

    # 後から確認
    uv run craft runs latest
    ```

---

## craft runs

veriq による verification run の履歴を確認するコマンド群。

### `craft runs list [--limit N]`

verification run の一覧を新しい順に表示する。

```bash
uv run craft runs list

# 最新 5 件のみ
uv run craft runs list --limit 5
```

**オプション**

| オプション | デフォルト | 説明 |
|---|---|---|
| `--limit N` | 20 | 表示件数の上限 |

---

### `craft runs show <run_id>`

指定した run の詳細を表示する。

```bash
uv run craft runs show 20260526_120000_abc
```

---

### `craft runs latest`

最新の verification run を表示する。

```bash
uv run craft runs latest
```

---

### `craft runs artifact <run_id> <name>`

指定した run のアーティファクトの内容を stdout に出力する。

```bash
uv run craft runs artifact 20260526_120000_abc result.toml

# ファイルに保存
uv run craft runs artifact 20260526_120000_abc result.toml > result.toml
```

**引数**

| 引数 | 説明 |
|---|---|
| `run_id` | verification run の ID |
| `name` | アーティファクト名（例: `result.toml`） |
