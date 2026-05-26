# Craft

**Concept Registry for Automated spacecraFT design**

宇宙機（衛星・深宇宙機含む）の概念設計を **型付き計算グラフ** として宣言的に記述する基盤。
`subsystems/<name>/components.py` に Python クラスを書くだけで、CLI / FastAPI / MCP (LLM agent) が自動的に配信される。

---

## 特徴

<div class="grid cards" markdown>

- :satellite: **宣言的**

    Component クラスを定義するだけで API・CLI・MCP tool が自動生成。
    `api/` / `cli/` / `mcp_server/` には一切触れない。

- :lock: **型安全**

    Pydantic v2 による完全な型検証。`fld()` で物理単位・制約・説明を宣言。
    JSON Schema が自動生成される。

- :rocket: **veriq 統合**

    `craft verify` 一発で全 subsystem の merge + 検証パイプライン実行。
    verification 結果は runs history に永続化される。

- :electric_plug: **マルチサーフェス**

    同一定義から CLI / REST API / MCP server の3 surface を自動配信。
    Swagger UI から GUI で操作できる。

</div>

---

## クイックスタート

```bash
# 1. インストール
uv sync

# 2. 登録済みコンポーネントを確認
uv run craft schema list

# 3. merge + veriq 検証を実行
uv run craft verify

# 4. API サーバ起動 → http://127.0.0.1:8000/docs
uv run uvicorn api.main:app --reload
```

---

## アーキテクチャ

```mermaid
graph TD
    A["subsystems/&lt;sub&gt;/components.py<br>configs.py / analyses.py"] -->|__init_subclass__<br>@analysis| B[UnifiedRegistry]
    C["subsystems/&lt;sub&gt;/data.toml"] -->|craft merge| D["generated/merged.toml"]
    B --> D
    D -->|craft verify| E["veriq 検証結果"]
    B --> F[FastAPI routers]
    B --> G[Typer CLI]
    B --> H[MCP server]
    E --> F
    E --> G
    E --> H
```

---

## ディレクトリ構成

```
craft/
├── schema/         # Component / Config base class, UnifiedRegistry, fld(), traits
├── core/           # TOML I/O, merge, scaffold, instance CRUD
├── api/            # FastAPI (routers/, errors.py, main.py)
├── cli/            # Typer CLI (craft コマンド)
├── mcp_server/     # MCP サーバ (craft-mcp, stdio)
├── subsystems/     # ユーザ領域 — ここだけ編集する
│   └── <name>/
│       ├── components.py
│       ├── configs.py
│       ├── analyses.py
│       ├── scope.py
│       └── data.toml
└── generated/      # merged.toml (生成物)
```

!!! tip "ユーザが触るのは `subsystems/` のみ"
    `schema/` / `core/` / `api/` / `cli/` / `mcp_server/` は基盤として固定されている。
    新しいコンポーネントを追加したいときは `subsystems/<name>/components.py` だけ編集する。

---

## 次のステップ

- [コア概念](concepts.md) — Component / Config / Analysis / Traits / `data.toml` の詳細
- [チュートリアル](tutorial.md) — 新しい subsystem をゼロから追加するハンズオン
- [CLI リファレンス](reference/cli/index.md) — 全コマンドの詳細説明
