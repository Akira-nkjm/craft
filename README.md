# Craft — Concept Registry for Automated spacecraFT design

宇宙機（衛星・深宇宙機含む）の概念設計を **「型付き計算グラフ」** として宣言的に記述し、CLI / FastAPI / Swagger UI / MCP（LLM agent）が同じ Pydantic 定義から自動派生する基盤。veriq による検証パイプラインとシームレスに統合する。

詳細な設計目標と背景は [`plan/Craft/Craft.md`](plan/Craft/Craft.md) を参照。

---

## アーキテクチャ

```
┌──────────────────────────────────────────────────────────────┐
│  Consumers                                                   │
│  CLI │ Swagger UI │ MCP (LLM agent) │ HTTP clients           │
└──────────────────────────────────────────────────────────────┘
                          │
┌──────────────────────────────────────────────────────────────┐
│  Public surface                                              │
│  FastAPI routers │ Typer CLI │ MCP server                    │
└──────────────────────────────────────────────────────────────┘
                          │  (introspect)
┌──────────────────────────────────────────────────────────────┐
│  UnifiedRegistry  (schema/)                                  │
│  Components / Configs / Analyses の定義一覧                  │
└──────────────────────────────────────────────────────────────┘
                          │  (registered by)
┌──────────────────────────────────────────────────────────────┐
│  Declarations  (subsystems/<name>/)                          │
│  components.py / configs.py / analyses.py / scope.py         │
└──────────────────────────────────────────────────────────────┘
                          │  (validated against)
┌──────────────────────────────────────────────────────────────┐
│  Data layer  (subsystems/<name>/data.toml)                   │
│   → core.merge → generated/merged.toml  (veriq 入力)         │
└──────────────────────────────────────────────────────────────┘
                          │  (computed by)
┌──────────────────────────────────────────────────────────────┐
│  Compute layer  — veriq (calc / verification / dep graph)    │
└──────────────────────────────────────────────────────────────┘
```

---

## ディレクトリ構成

フラット構成。ユーザが直接触るのは `subsystems/` のみで、`schema/` は基盤として固定する。

```
craft/
├── schema/                 # 基盤: Component / Config base class, UnifiedRegistry
├── core/                   # TOML I/O, merge, scaffold, instance CRUD
├── api/                    # FastAPI 本体 (routers/, errors.py, main.py)
├── cli/                    # Typer CLI エントリ (craft コマンド)
├── mcp_server/             # MCP サーバ (craft-mcp、stdio)
├── subsystems/             # ユーザ領域 (power / cdh / thermal / mission)
│   └── <name>/
│       ├── components.py   # Component 派生クラス
│       ├── configs.py      # Config 派生クラス
│       ├── analyses.py     # @analysis 関数
│       ├── scope.py        # vq.Scope 定義
│       └── data.toml       # インスタンスデータ
├── generated/              # merged.toml / merged.lock など生成物
├── tests/                  # pytest (72 件)
├── plan/                   # 設計ドキュメント
├── pyproject.toml          # uv 単一プロジェクト
└── README.md
```

---

## セットアップ

```bash
uv sync
```

`uv` が未導入の場合は <https://docs.astral.sh/uv/> を参照。Python 3.14 以上が必要。

---

## 基本コマンド

```bash
# CLI ヘルプ
uv run craft --help

# 登録済み subsystem / component の一覧
uv run craft schema list

# merge + veriq による検証実行
uv run craft verify

# FastAPI 起動 → Swagger UI: http://127.0.0.1:8000/docs
uv run uvicorn api.main:app --reload

# MCP サーバ (stdio) — Claude Code / Desktop から利用
uv run craft-mcp
```

主な CLI サブコマンド:

```bash
uv run craft schema show <sub> <comp>       # JSON Schema 表示
uv run craft get <sub> <comp> [<inst>]      # インスタンス取得
uv run craft merge [--check] [--dry-run]    # data.toml → merged.toml
uv run craft scaffold [<sub>] [--dry-run]   # data.toml 雛形生成
uv run craft analysis list                  # @analysis 一覧
uv run craft analysis run <sub> <name>      # @analysis 実行
uv run craft init subsystem <name>          # subsystem 雛形生成
```

---

## 検査コマンド

```bash
uv run pytest                # 全テスト
uv run ruff check .          # Lint
uv run pyrefly check         # 型チェック
```

---

## `data.toml` の簡略形式

`subsystems/<name>/data.toml` では `<sub>.model.` プレフィックスを省略して記述する（`core.merge` が `generated/merged.toml` 生成時に自動付与）。`shared_spec=True` の MultiInstance Component は、共通の `spec` と instance ごとの `design` / `requirements` / `meta` を分離する。

例: `subsystems/power/data.toml`

```toml
# 全インスタンス共通の spec
[batteries.spec]
capacity_wh = 100.0
nominal_voltage_v = 3.7

# instance "main" の固有設定
[batteries.main.design]
depth_of_discharge = 0.7

[batteries.main.requirements]
depth_of_discharge_max = 0.8

# instance "aux"
[batteries.aux.design]
depth_of_discharge = 0.6
```

`uv run craft merge` で `generated/merged.toml` に統合され、`[power.model.batteries.spec]` の形式に展開される。`tomlkit` を用いてコメントは保持される。

---

## 関連ドキュメント

- [`plan/Craft/Craft.md`](plan/Craft/Craft.md) — プロジェクト全体の入口
- [`plan/Craft/最終構成.md`](plan/Craft/最終構成.md) — 目標アーキテクチャ（唯一の真）
- [`AGENTS.md`](AGENTS.md) — AI エージェント向け統一ガイダンス
- [`CLAUDE.md`](CLAUDE.md) — Claude Code 向け追加情報
- [`.claude/rules/`](.claude/rules/) — 詳細ルール（アーキテクチャ / コマンド / Git / セキュリティ）
