# craft 開発ツール

型スタブ生成・プロジェクト初期化・履歴確認など、開発を支援するコマンド群。

---

## craft gen-stubs

各 subsystem に型スタブファイル (`_stubs.pyi`) を生成する。エディタの補完や静的解析が改善される。

### `craft gen-stubs [--check]`

```bash
# スタブを生成
uv run craft gen-stubs

# CI 用チェック（stale なら exit 1）
uv run craft gen-stubs --check
```

**オプション**

| オプション | 説明 |
|---|---|
| `--check` | stubs が最新かどうかを確認し、stale なら exit 1（CI 用） |

**生成されるファイル**

```
subsystems/<name>/_stubs.pyi   # Component / Config の型情報
```

!!! tip "CI での使い方"
    ```yaml
    - name: Check stubs are up to date
      run: uv run craft gen-stubs --check
    ```

---

## craft init

新しい subsystem の雛形ディレクトリを生成する。

### `craft init subsystem <name> [--kind]`

```bash
# ハードウェア系 subsystem
uv run craft init subsystem propulsion --kind hardware

# 設定専用 subsystem（Config のみ）
uv run craft init subsystem mission_config --kind config-only

# 最小スケルトン
uv run craft init subsystem experimental --kind default
```

**引数・オプション**

| 引数 / オプション | デフォルト | 説明 |
|---|---|---|
| `name` | — | 新しい subsystem の名前 |
| `--kind` | `hardware` | `hardware` / `config-only` / `default` |

**`--kind` の違い**

| 値 | 生成されるファイル |
|---|---|
| `hardware` | `components.py` + `configs.py` + `analyses.py` + `scope.py` + `data.toml` |
| `config-only` | `configs.py` + `scope.py` + `data.toml` |
| `default` | 最小スケルトン（`scope.py` + `data.toml`） |

**生成後の Next Steps**（コマンド実行時に表示される）

```
1. edit subsystems/<name>/components.py (or configs.py)
2. craft scaffold <name>
3. fill values in subsystems/<name>/data.toml
4. craft verify
```

---

## craft history / diff

Git 履歴と差分を確認するコマンド群。設計変化のトレースや、特定コミット間の比較に使う。

### `craft history [<path>] [--limit N]`

git log を JSON 形式で出力する。

```bash
# リポジトリ全体の履歴
uv run craft history

# 特定ファイルの履歴
uv run craft history subsystems/power/data.toml

# 最新 10 件のみ
uv run craft history --limit 10
```

**引数・オプション**

| 引数 / オプション | デフォルト | 説明 |
|---|---|---|
| `path` | リポジトリ全体 | 履歴を絞り込むファイル / ディレクトリ |
| `--limit N` | 20 | 表示件数の上限 |

**出力例**

```json
{
  "path": "subsystems/power/data.toml",
  "entries": [
    {
      "sha": "d39b1f0",
      "author": "Akira",
      "date": "2026-05-20T10:00:00+09:00",
      "message": "feat: add aux battery instance"
    }
  ]
}
```

---

### `craft diff <from_sha> <to_sha> [<path>]`

2 つの git ref 間の差分を表示する。

```bash
# 2 コミット間の全差分
uv run craft diff d39b1f0 9403cb4

# 特定ファイルの差分のみ
uv run craft diff d39b1f0 9403cb4 subsystems/power/data.toml

# 相対 ref も使える
uv run craft diff HEAD~3 HEAD subsystems/power/data.toml
```

**引数**

| 引数 | 説明 |
|---|---|
| `from_sha` | 差分の起点となる git ref（SHA / ブランチ名 / タグ / `HEAD~N` 等） |
| `to_sha` | 差分の終点となる git ref |
| `path` | 差分を絞り込むファイル / ディレクトリ（省略時は全体） |

---

## 付録: CI チェックリスト

GitHub Actions 等の CI で使うコマンドの組み合わせ例：

```yaml
- name: Lint & type check
  run: |
    uv run ruff check .
    uv run pyrefly check

- name: Test
  run: uv run pytest -q

- name: Check merge is up to date
  run: uv run craft merge --check

- name: Check stubs are up to date
  run: uv run craft gen-stubs --check

- name: Run verification
  run: uv run craft verify
```
