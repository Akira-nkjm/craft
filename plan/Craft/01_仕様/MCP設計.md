---
project: "Craft"
tags: [project, dev, satellite, spec, mcp]
date_updated: 2026-05-26
---

# MCP 設計 — LLM 連携サーバ

> 親: [[最終構成]] / 関連: [[UnifiedRegistry設計]] / [[API設計]] / [[テスト戦略]]

`mcp/server.py` の設計。**registry を tool として公開し、Claude Code / Desktop から直接対話できる** ことを目的とする。

LLM 連携の方式選定（MCP vs Function Calling vs propose ループ）は [[最終構成]] §10-1 で MCP に確定済み。本ノートはその実装仕様を具体化する。

---

## 1. 方針

### 1.1 採用する原則

1. **registry 由来の自動派生** — Component / Config / Analysis の宣言が増えると、対応する MCP tool が自動的に増える
2. **API/CLI/MCP は三兄弟** — 同じ registry を 3 種類の surface に露出する。実装の重複を作らない（[[最終構成]] §3）
3. **stateless** — MCP サーバはデータを持たない。すべての状態は TOML / runs/ にあり、サーバは API の薄ラッパ
4. **ローカル専用** — Claude Code / Desktop からの stdio 接続のみ。リモート公開は想定しない（認証なし）

### 1.2 やらないこと

- ❌ **propose ループの自動化** — LLM 側に判断ループを持たせる実装はしない。tool を呼ぶ判断は LLM に任せる（[[最終構成]] §10-1 「propose ループは将来」）
- ❌ **MCP 専用のビジネスロジック** — registry 経由でない処理は MCP に書かない。書きたくなったら API か analysis に置く
- ❌ **書き込み tool のロールバック機構** — TOML は git 管理、必要なら git revert で戻す（[[対処方針]] §D.1）

---

## 2. tool 一覧と命名規約

registry から自動派生する tool を **5 系統** に分類する。

### 2.1 Component CRUD（hardware）

| tool | 由来 | 例 |
|---|---|---|
| `list_<plural>` | 各 Multi-instance Component | `list_batteries`, `list_solar_panels` |
| `get_<singular>` | 各 Component | `get_battery`, `get_obc` |
| `add_<singular>` | 各 Multi-instance Component | `add_battery(name, spec, design, requirements)` |
| `update_<singular>` | 各 Component | `update_battery(name, ...)` |
| `delete_<singular>` | 各 Multi-instance Component | `delete_battery(name)` |

Singleton hardware（OBC 等）は `get_<singular>` と `update_<singular>` のみ（add/delete なし）。

### 2.2 Config 操作

| tool | 由来 | 例 |
|---|---|---|
| `get_<config>` | 各 Config | `get_mission_profile`, `get_orbital_parameters` |
| `set_<config>` | 各 Config | `set_mission_profile(...)` |

Config は常に Singleton なので list / add / delete なし（[[Config設計]] §2.3）。

### 2.3 Analysis 実行

| tool | 由来 | 例 |
|---|---|---|
| `analyze_<name>` | 各 `@analysis` | `analyze_battery_eol_capacity(years=5, ...)` |
| `verify_<name>` | 各 `@analysis(verify=True)` | `verify_battery_capacity()` |
| `verify_subsystem` | 共通 | `verify_subsystem(name="power")` |
| `verify_all` | 共通 | `verify_all()` |

### 2.4 Introspection（registry 照会）

| tool | 役割 |
|---|---|
| `list_subsystems` | 登録済み subsystem 一覧 |
| `list_components` | 全 component の (subsystem, name, plural, fields) |
| `list_configs` | 全 config の (subsystem, name, fields) |
| `list_analyses` | 全 analysis の (name, signature, tags) |
| `search_field` | フィールド名・型で横断検索 |
| `get_schema` | 指定 component / config の JSON Schema |

→ [[API設計]] §Cross-component Query / `/api/registry/...` と 1:1 対応。

### 2.5 履歴・diff

| tool | 役割 |
|---|---|
| `history` | TOML 変更履歴（git log 由来） |
| `diff` | 任意の 2 点間 diff |
| `latest_run` | 最新検証結果 |
| `get_run` | 指定 run_id の結果取得 |

### 2.6 命名規約（強制）

- **動詞 + 名詞**: `add_battery` (✅) / `battery_add` (❌)
- **snake_case**: `add_solar_panel` (✅) / `addSolarPanel` (❌)
- **plural は registry の `plural` 属性を尊重**: `add_battery` で TOML は `[batteries.<name>]` に書かれる
- **subsystem は引数に含めない**: `add_battery` だけで OK（component 名が一意なので subsystem 不要）

---

## 3. tool 入出力スキーマ

### 3.1 入力 schema は registry から JSON Schema を生成

```python
# 概念
def get_tool_schema(component_name: str) -> dict:
    defn = registry.get_component(component_name)
    return {
        "name": f"add_{defn.singular}",
        "description": f"Add a {defn.name} instance",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Instance name"},
                "spec": defn.spec_schema(),       # Pydantic JSON Schema
                "design": defn.design_schema(),
                "requirements": defn.requirements_schema(),
            },
            "required": ["name", "spec", "design"]
        }
    }
```

→ Component の field を増やすと **MCP tool の inputSchema も自動更新**。

### 3.2 出力形式

- 通常: tool 呼び出しの戻り値を MCP の `content` に JSON 文字列でラップ
- エラー: API と同じ RFC 7807 互換 envelope（[[最終構成]] §5.4）

```json
{
  "type": "validation_error",
  "status": 422,
  "title": "Input validation failed",
  "errors": [{"loc": ["spec", "capacity_wh"], "msg": "..."}]
}
```

### 3.3 `vq.Ref` を含む analysis の扱い

`@analysis` 関数が `vq.Ref` で TOML 参照を引く場合、MCP tool 側では **直接パラメータだけ** を入力に取る（Ref 引数は内部で解決）。

```python
@analysis
def battery_eol_capacity(
    batteries: Annotated[..., vq.Ref("$.batteries")],   # ← tool input から隠す
    years: float,                                       # ← tool input に出す
    cycles_per_day: float = 1.0,
) -> EolResult: ...
```

→ MCP tool は `analyze_battery_eol_capacity(years, cycles_per_day)` の 2 引数のみ受け付ける。

---

## 4. 実装構造

```
mcp/
├── server.py            # MCP サーバ entry point（stdio）
├── tool_factory.py      # registry → tool 定義を生成する純粋関数
├── handlers/
│   ├── crud.py          # add/update/delete/get/list の共通実装
│   ├── analysis.py      # analyze_* / verify_* の共通実装
│   ├── introspect.py    # list_components 等の registry 照会
│   └── history.py       # history / diff / runs
└── tests/               # 各 handler の unit + 系統 C E2E
```

### 4.1 起動シーケンス

```
mcp serve
  ↓
default_registry をロード（[[UnifiedRegistry設計]] §6.1）
  ↓
tool_factory.build_all_tools(registry) → list[ToolDefinition]
  ↓
MCP SDK の Server を起動、tools/list と tools/call を実装
  ↓
stdio で待ち受け
```

### 4.2 内部実装は API を呼ぶ

```python
# 例: add_battery tool
async def handle_add_battery(args):
    return await api_client.post(
        f"/api/projects/default/components/power/battery/{args['name']}",
        json={"spec": args["spec"], "design": args["design"], ...},
    )
```

→ **MCP は API の薄ラッパ**。ロジックを 2 重実装しない（[[最終構成]] §3 「decorator が増えても土台は増えない」）。

---

## 5. テスト戦略との対応

[[テスト戦略]] §系統C で定義された MCP E2E に従う:

```python
from mcp import Client

async def test_mcp_add_battery():
    async with Client("python -m craft.mcp.server") as client:
        tools = await client.list_tools()
        assert "add_battery" in [t.name for t in tools]

        result = await client.call_tool("add_battery", {
            "name": "test_battery",
            "spec": {"capacity_wh": 100, ...},
            "design": {...},
        })
        assert result.is_success
```

`mainブランチでのみ実行`（[[テスト戦略]] §174）— MCP サーバ起動コストがあるため。

---

## 6. 認証・権限

### 6.1 Phase 1: 認証なし

- stdio 経由のローカル接続のみ
- Claude Code / Desktop が同一マシンで起動
- API と同じ `127.0.0.1` バインドの考え方（[[対処方針]] §C.2）

### 6.2 Phase 2 以降: 必要に応じて

- MCP の `clientInfo` を見て tool を絞る（write tool を読み取り専用クライアントに見せない）
- リモート公開する場合は MCP の transport を WebSocket + bearer token に切り替える

---

## 7. propose ループ（Phase 2+）

[[最終構成]] §10-1 で「propose ループは将来」と確定済み。Phase 1 では実装しない。

Phase 2+ で実装する場合の素案:

```
ユーザの要求（自然言語）
  ↓
LLM に MCP tool 一覧を渡す（既存の tool でカバー可能）
  ↓
LLM が tool を順次呼んで設計を組み立てる
  ↓
verify_all を呼んで充足判定
  ↓ 不合格
LLM に結果をフィードバック → LLM が修正案を出す
  ↓ 反復
```

→ **新規 MCP 機能は不要**。既存 tool の組み合わせで実現できる設計を維持する。

---

## 8. 確定事項

| 項目 | 決定 |
|---|---|
| 接続 | stdio（ローカル専用） |
| 認証 | Phase 1 では無し |
| tool 派生 | registry から自動、手書きの tool は禁止 |
| 命名規約 | `動詞_名詞` (snake_case)、subsystem は引数に含めない |
| 入力 schema | Pydantic JSON Schema をそのまま MCP `inputSchema` に流用 |
| エラー形式 | API と同じ RFC 7807 互換 envelope |
| 実装 | API client の薄ラッパ、ロジック重複なし |
| Ref 引数 | tool input から隠す（内部で解決） |

---

## 9. 残る論点

- **動的 enum と tool schema の同期**: TOML に新 instance を足すと enum 値が増えるが、MCP 側は起動時に tool schema を固定する。動的更新が必要か？
  - 暫定方針: tool schema は固定、enum 値の妥当性は実行時 422 で弾く（API と同じ）
- **長時間解析の進捗報告**: `analyze_*` tool が job 化された時、MCP の `progress` notification をどう使うか
- **複数プロジェクト対応**: Phase 2 で `/api/projects/{pid}/...` に切る場合、MCP tool に project_id 引数を足すか、サーバ起動時に固定するか
- **tool 数の爆発**: subsystem が増えると tool 数が `O(component × CRUD)` で増える。Claude 側の表示で困らないか実測が必要

→ 実装着手時に確認、本ノートに追記。
