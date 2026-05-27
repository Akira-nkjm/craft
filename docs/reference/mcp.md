# MCP サーバ

Craft は **MCP (Model Context Protocol) サーバ** (`craft-mcp`) を同梱しており、
Claude Code / Claude Desktop など MCP 対応のエージェントから自然言語で
コンポーネント・設定・解析を操作できる。

CLI / FastAPI と同じ registry を共有しているため、`systems/<name>/components.py` に
新しい Component を追加すると **MCP tool も自動で増える**（再実装は不要）。

---

## 起動方法

```bash
# 直接起動（stdio）
uv run craft-mcp
```

`craft-mcp` は `pyproject.toml` の `[project.scripts]` に登録されている
コンソールスクリプト。stdio で JSON-RPC 2.0 を喋るので、対話的に叩くのではなく
MCP クライアント（Claude Code / Desktop 等）から接続する。

### Claude Code / Desktop への登録

リポジトリ同梱の [`.mcp.json`](https://github.com/Akira-nkjm/craft/blob/main/.mcp.json) を参考に、
クライアント設定で以下のように登録する:

```json
{
  "mcpServers": {
    "craft": {
      "command": "uv",
      "args": ["--directory", "/path/to/craft", "run", "craft-mcp"]
    }
  }
}
```

Claude Desktop の場合は `~/Library/Application Support/Claude/claude_desktop_config.json`
に同じ形式で書く。Claude Code の場合は repo ルートに `.mcp.json` を置けば
プロジェクトを開いたときに自動で接続される。

!!! tip "接続確認"
    Claude Code で接続できているかは `/mcp` 一覧、または
    `list_systems` ツールが見えるかどうかで確認できる。

---

## ツール体系

`mcp_server/tool_factory.py` が **registry を走査して** 以下のカテゴリの tool を
動的生成する。

| カテゴリ | 例 | 説明 |
|---|---|---|
| Introspection | `list_systems` / `list_components` / `list_configs` / `list_analyses` / `get_schema` | registry を読み出す |
| Component (Singleton) | `get_<name>` / `patch_<name>` | 単一インスタンスの取得・部分更新 |
| Component (MultiInstance) | `list_<plural>` / `get_<name>` / `add_<name>` / `patch_<name>` / `delete_<name>` / `set_<plural>_spec` | 複数インスタンスの CRUD と共有 spec 更新 |
| Config (single) | `get_<name>` / `set_<name>` | Config 全置換 |
| Config (multi) | `list_<plural>` / `get_<name>` / `set_<name>` / `patch_<name>` / `delete_<name>` | 名前付き Config エントリの CRUD |
| Analysis | `analyze_<name>` | `@analysis` を 1 件実行（veriq バインド型 + ad-hoc 型） |
| Verify | `verify_all` / `verify_<name>` | 全 verification または個別 verification を実行 |
| History | `history` / `diff` | git log / git diff |

!!! note "自動生成の仕組み"
    tool 名は `default_registry` に登録された Component / Config / Analysis から
    自動で決まる。`<name>` は Component / Config クラス名を `lower()` した値、
    `<plural>` は `Component(plural=...)` または自動 plural を使う。

---

## Introspection — registry を読む

| Tool | 入力 | 出力 |
|---|---|---|
| `list_systems` | なし | 登録済み system 名の配列 |
| `list_components` | なし | `(system, name, plural, cardinality, traits)` の配列 |
| `list_configs` | なし | `(system, name)` の配列 |
| `list_analyses` | なし | `(system, name, verify, desc)` の配列 |
| `get_schema` | `{ system, component }` | Component の JSON Schema (Entry model) |

LLM エージェントは通常、**最初に `list_systems` → `list_components`** で
何が触れるか確認してから個別の `get_*` / `patch_*` を呼ぶ。

---

## Component を操作する

### Singleton（単一インスタンス）

```text
get_obc()                       → 現在の cdh.obc を返す
patch_obc({delta: {...}})        → 部分更新
```

入力スキーマ:

```json
{
  "delta": { "type": "object" },
  "etag":  { "type": "string" }
}
```

`delta` は深いマージで適用される。`etag` を指定すると楽観的排他制御が効く。

### MultiInstance（複数インスタンス + 共有 spec）

```text
list_batteries()                            → power.battery の全インスタンス
get_battery({name: "main"})                 → 1 件取得
add_battery({name: "aux", design: {...}})   → 新規作成
patch_battery({name: "main", delta: {...}}) → 部分更新
delete_battery({name: "old"})               → 削除
set_batteries_spec({spec: {...}})           → 共有 spec を全置換
```

`spec` セクションは MultiInstance の全インスタンスで共有される
（[コア概念 — Singleton vs MultiInstance](../concepts.md#singleton-vs-multiinstance)）。
個別 instance の `design` / `requirements` だけを変えたいときは `patch_<name>`、
カタログ値（同型バッテリの容量・電圧等）をまとめて変えたいときは
`set_<plural>_spec` を使う。

!!! tip "ETag のセマンティクスは CLI/API と同じ"
    `get_*` の戻り値に含まれる `etag` を `patch_*` / `delete_*` / `set_*_spec` に
    渡すと、別エージェントによる先行更新を 409 として検出できる。
    `etag` を省略するとサーバ側で自動取得するので、単一エージェント運用なら省略してよい。

---

## Config を操作する

### 単一 Config（フラット）

```text
get_missionprofile()
set_missionprofile({data: { duration_years: 5.0, ... }})
```

`set_*` は **全置換**。部分更新したい場合は `get_*` で取得して merge してから
`set_*` に渡す（または Multi Config の `patch_*` を使う）。

### MultiInstance Config（名前付きエントリ）

```text
list_operation_mode_configs()
get_operationmodeconfig({key: "nominal"})
set_operationmodeconfig({key: "nominal", data: {...}})    # 作成 or 全置換
patch_operationmodeconfig({key: "nominal", delta: {...}}) # 部分更新
delete_operationmodeconfig({key: "old"})
```

`OperationModeConfig` のような「名前付きパターンの集合」を扱う Config に
このパターンが使われる。

---

## Analysis を実行する

### veriq バインド型（自動引数）

入力は不要。veriq が `vq.Ref(...)` 経由でデータを注入する。

```text
analyze_total_pdm_power_w()
→ { "value": 8.0, "cache_hit": false }

analyze_required_orbit_energy_wh()
→ { "value": 0.533, "cache_hit": false }
```

### ad-hoc 型（CLI と同じく `--payload` 相当を引数で渡す）

`@analysis(system=None, ...)` で登録した関数。
inputSchema は **関数シグネチャから自動生成** される。

```text
analyze_battery_eol_capacity({
  "initial_capacity_wh": 100.0,
  "years": 3.0,
  "cycles_per_day": 1.0
})
→ { "value": 89.075, "cache_hit": false }
```

| Python annotation | JSON Schema type |
|---|---|
| `float` | `number` |
| `int` | `integer` |
| `bool` | `boolean` |
| その他・未指定 | `string` |

!!! note "verify=True の analysis は `analyze_*` には現れない"
    `@analysis(verify=True, ...)` の関数は verification 用 tool
    （`verify_<name>` 系）として別に公開される。

---

## Verification を実行する

```text
verify_all()
→ {
    "success": true,
    "errors": 0,
    "run_id": "20260526_120000_abc",
    "results": [
      { "scope": "power", "name": "verify_battery_capacity", "value": true },
      ...
    ]
  }

verify_verify_battery_capacity()
→ 単一 verification の結果
```

`verify_all` は CLI の `craft verify` と同等で、自動的に merge → veriq evaluate を
実行する。実行ごとに verification run が永続化されるので、`history` 系 tool や
`/runs` API / `craft runs` から後で参照できる。

---

## History / Diff — 設計変更を追跡

```text
history({ path: "systems/power/data.toml", limit: 10 })
→ git log エントリの配列（sha / author / date / message）

diff({ from: "HEAD~3", to: "HEAD", path: "systems/power/" })
→ 2 つの ref 間の diff（path 省略時は全体）
```

`craft history` / `craft diff` CLI と同じ実装を使うので、出力フォーマットも揃っている。

---

## 動作確認（手動プローブ）

stdio で JSON-RPC を直接叩いて疎通確認できる:

```bash
uv run craft-mcp <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
EOF
```

`tools/list` の結果に `list_systems` / `get_obc` / `analyze_total_pdm_power_w` などが
並んでいれば正常起動している。

---

## トラブルシュート

| 症状 | 原因 / 対処 |
|---|---|
| `unknown tool: <name>` | `default_registry` に未登録。`craft schema list` で確認し、`systems/<sub>/__init__.py` から `components` を import しているか確認 |
| `get_*` が 404 相当のエラー | `data.toml` にそのインスタンス（または key）が存在しない。`list_*` で確認 |
| `patch_*` が 409 相当のエラー | ETag mismatch（他で更新されている）。再取得してから retry |
| Verification が失敗するが理由が分からない | `craft runs latest` または `runs artifact` で詳細を確認 |

---

## 関連

- [CLI リファレンス](cli/index.md) — 同じ操作を端末から行う
- [REST API リファレンス](api.md) — 同じ操作を HTTP で行う
- [コア概念](../concepts.md) — Component / Config / Analysis の意味
