# アーキテクチャ・ファイル構成

> プロジェクトごとに編集するテンプレート。コードから読み取れない「なぜ」を中心に書く。

## システム概要

宇宙機の概念設計を Pydantic による「型付き計算グラフ」として宣言的に記述する基盤。
1 つの型定義から CLI / FastAPI(Swagger UI) / MCP を自動派生させ、検証・計算は veriq に委譲する。

## データフロー / 処理パイプライン

```
systems/<name>/{components,configs,analyses,scope}.py   ← Pydantic 定義
   ↓ (register)
UnifiedRegistry  (craft.schema)                          ← 定義一覧
   ↓ (introspect)
公開面: FastAPI routers / Typer CLI / MCP server         ← 同じ定義から自動派生
   ↑
systems/<name>/data.toml  (簡略形式)
   ↓ core.merge
generated/merged.toml                                    ← veriq 入力
   ↓ compute
veriq (calc / verification / dep graph)                  ← 検証・計算結果
```

## コアモジュール

- **`src/craft/schema/`** — 基盤。`Component` / `Config` base class と `UnifiedRegistry`
- **`src/craft/core/`** — TOML I/O, merge, scaffold, instance CRUD（`data.toml` → `merged.toml`）
- **`src/craft/api/`** — FastAPI 本体（`routers/`, `errors.py`, `main.py`）
- **`src/craft/cli/`** — Typer CLI エントリ（`craft` コマンド）
- **`src/craft/mcp_server/`** — MCP サーバ（`craft-mcp`, stdio）
- **`systems/<name>/`** — ユーザ領域。`components.py` / `configs.py` / `analyses.py` / `scope.py` / `data.toml`
- **`systems/project.py`** — veriq CLI エントリポイント
- **`generated/`** — `merged.toml` / `merged.lock` などの生成物
- **`tests/`** — pytest（`craft/` / `systems/` / `integration/` / `fixtures/`）

## レイヤー構成と依存方向

```
Consumers (CLI / Swagger UI / MCP / HTTP)
   → 公開面 (FastAPI / Typer / MCP server)
   → UnifiedRegistry (craft.schema)
   → Declarations (systems/<name>/)
   → Data (data.toml → merged.toml)
   → Compute (veriq)
```

- `systems/`（ユーザ領域）は `src/craft/`（framework）に依存してよいが、逆は不可。
- `craft` → `veriq` の一方向依存。veriq を craft に依存させない。

## 設計判断（なぜこうなっているか）

- **なぜ Pydantic を single source of truth にするか** — CLI / API / MCP / JSON Schema を 1 つの型定義から
  自動派生させ、手書きスキーマの二重管理とドリフトを排除するため。
- **なぜ framework（`src/craft/`）とユーザ領域（`systems/`）を分けるか** — ユーザが触る面を `systems/` の
  宣言だけに絞り、framework 実装の複雑さを隠蔽するため。
- **なぜ `data.toml` は簡略形式か** — 設計者が `<sub>.model.` プレフィックス無しで素直に書けるようにし、
  `core.merge` が機械的に正規化する。`tomlkit` でコメントを保持し、人が編集する前提を守る。
- **なぜ計算を veriq に委譲するか** — 検証・計算グラフは独立して再利用・テストできる別ライブラリに切り出し、
  craft は「定義と公開面」に専念するため。

## ファイルツリー

```
craft/
├── CLAUDE.md / .claude/        # Claude 向けガイダンス・ルール
├── src/craft/                  # framework 本体（craft.* モジュール）
│   ├── schema/                 # Component / Config base, UnifiedRegistry
│   ├── core/                   # TOML I/O, merge, scaffold, CRUD
│   ├── api/                    # FastAPI (routers/, errors.py, main.py)
│   ├── cli/                    # Typer CLI (craft)
│   └── mcp_server/             # MCP サーバ (craft-mcp)
├── systems/                    # ユーザ領域 (power / cdh / thermal / mission ...)
│   ├── project.py              # veriq CLI エントリ
│   └── <name>/                 # components/configs/analyses/scope.py + data.toml
├── generated/                  # merged.toml / merged.lock など生成物
├── tests/                      # pytest
├── docs/                       # Zensical ドキュメント
├── plan/                       # 設計ドキュメント（最終構成.md が正典）
└── pyproject.toml              # uv 単一プロジェクト
```

## よくあるワークフロー

### 新しい system を追加

1. `uv run craft init system <name>` で雛形を生成
2. `systems/<name>/` の `components.py` / `configs.py` / `analyses.py` / `scope.py` を実装
3. `systems/<name>/data.toml` にインスタンスデータを記述
4. `uv run craft merge` → `generated/merged.toml` を確認、`uv run craft verify` で検証
5. `uv run pytest` / `uv run ruff check .` / `uv run pyrefly check` を通してコミット

### 既存 system のデータ変更

1. `systems/<name>/data.toml` を編集
2. `uv run craft merge --check`（または `--dry-run`）で差分確認
3. `uv run craft verify` で veriq 検証を実行
