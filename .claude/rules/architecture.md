# アーキテクチャ・ファイル構成

> Craft 実コードの構造。コードから読み取れない「なぜ」を中心に書く。

## システム概要

Craft (Concept Registry for Automated spacecraFT design) は、宇宙機の概念設計を Pydantic で型付けされた Component / Config / Analysis として宣言的に記述し、CLI / FastAPI / MCP の 3 つの surface へ自動配信する基盤。データは `systems/<name>/data.toml` に保存し、veriq による検証パイプラインと統合する。

## データフロー / 処理パイプライン

```
systems/<sys>/components.py, configs.py, analyses.py
    ↓  (__init_subclass__ で UnifiedRegistry へ自動登録)
schema.default_registry  (Components / Configs / Analyses)
    ↓  (core.discovery.discover_systems が import 駆動)
systems/<sys>/data.toml
    ↓  (core.merge: tomlkit でコメント保持、<sys>.model.* プレフィックス付与)
generated/merged.toml
    ↓  (vq.evaluate_project)
veriq 計算結果 + verification（成功/失敗）
    ↓
CLI 表示 / API レスポンス / MCP tool result
```

## コアモジュール

- **`src/craft/schema/`** (`craft.schema`) — Component / Config base class、Pydantic ベースの UnifiedRegistry（`__init_subclass__` で登録）、`fld()`、traits、root_model builder
- **`src/craft/core/`** (`craft.core`) — TOML I/O（`tomlkit`）、`merge`、`scaffold`、instance CRUD（ETag）、ファイルパス解決、`discover_systems`、`runs` / `history` / `jobs` / `analysis_cache` / `verify`
- **`src/craft/api/`** (`craft.api`) — FastAPI 本体。`main.py` で lifespan に discovery を仕込み、`routers/{schema,components,configs,merge,scaffold,verify,analyses,runs,history,veriq_passthrough}.py` を mount
- **`src/craft/cli/`** (`craft.cli`) — Typer CLI (`craft` コマンド)。`schema` / `get` / `merge` / `scaffold` / `verify` / `runs` / `analysis` / `init` サブコマンド
- **`src/craft/mcp_server/`** (`craft.mcp_server`) — `craft-mcp`（stdio）。registry から MCP tool を自動生成（`tool_factory.py`）
- **`systems/<name>/`** — ユーザ領域。`components.py` / `configs.py` / `analyses.py` / `scope.py` / `data.toml`。`systems/project.py` は veriq の CLI エントリポイント
- **`generated/`** — `merge` の出力（`merged.toml` / `merged.lock` / `runs/`）

## レイヤー構成と依存方向

```
systems/  →  craft.schema, craft.core  →  craft.api, craft.cli, craft.mcp_server
```

- `systems/` は `craft.schema` / `craft.core` / `veriq` のみに依存
- `craft.api` / `craft.cli` / `craft.mcp_server` は `craft.core` と `craft.schema` を介して systems を間接的に扱う
- `craft.schema` と `craft.core` は他のどの層にも依存しない（循環禁止）

## 設計判断（なぜこうなっているか）

- **`src/craft/` レイアウトを採用** — framework 実装（`schema` / `core` / `api` / `cli` / `mcp_server`）と user 領域（`systems/`）を視覚的に分離するため、framework 本体を `src/craft/` 配下に集約した。ユーザが root を見たときに「自分が触るのは `systems/` だけ」が一目で分かる。uv workspace で member 化する案は議論されたが、Craft は単一プロジェクトとして配布する想定で `craft.*` モジュール群は同一バージョンで動く必要があるため、`pyproject.toml` の `packages = ["src/craft", "systems"]` で単一 wheel としてビルドする。
- **`shared_spec=True` を採用（MultiInstance Component）** — 同種ハードウェア（同型バッテリ × 2 など）の `spec` は instance 間で共有が普通。TOML を `[batteries.spec]` + `[batteries.<name>.design]` に分けることで重複を排除し、選定変更時の差分も最小化する。
- **`data.toml` で `<sys>.model.` プレフィックスを省略** — ユーザが書くのは「system 内の論理構造」だけにし、veriq 規約（`[<scope>.model.<...>]`）への変換は `core.merge` が担う。これで TOML の可読性と veriq との整合性を両立する。
- **`tomlkit` でコメント保持** — `tomli-w` は書き込みでコメントを失う。`data.toml` はユーザが手で編集する一次資料なので、コメント・順序・空行を保持する `tomlkit` を merge / scaffold の両方で使う。
- **`fld() -> Any` (Pydantic 公式 + `dataclass_transform`)** — Pydantic v2 公式が推奨する dataclass_transform パターンで、`fld(default=..., gt=..., description=...)` を型推論に正しく流す。これにより Component / Config の宣言が dataclass ライクになり、ボイラープレートが大幅に減る。
- **`from __future__ import annotations` 禁止** — `inspect.signature` 経由で実行時型を読む veriq との互換性を壊すため。型ヒントは常に実体を書く。

## ファイルツリー

```
craft/
├── AGENTS.md / CLAUDE.md / RULES.md / SOUL.md
├── README.md
├── pyproject.toml          # uv 単一プロジェクト、hatchling
├── justfile                # 補助タスク
├── src/craft/              # framework 本体（craft.* import パス）
│   ├── schema/             # Component / Config / Registry / fld / traits
│   ├── core/               # merge, scaffold, instances, discovery, toml_io
│   ├── api/                # FastAPI (main.py + routers/)
│   ├── cli/                # Typer CLI
│   └── mcp_server/         # MCP サーバ (stdio)
├── systems/                # aocs / cdh / mission / orbital / power / thermal
│   └── project.py          # veriq CLI エントリポイント
├── generated/              # merged.toml / merged.lock / runs/
├── tests/                  # pytest
├── plan/                   # 設計ドキュメント
└── .claude/                # Claude Code 設定 + rules
```

## よくあるワークフロー

### 新しい Component を追加する

1. `systems/<sys>/components.py` に `class X(Component, traits=[...]): ...` を追記
2. `uv run craft scaffold <sys>` で `data.toml` に雛形を追加（既存値は保持）
3. `data.toml` に instance を書く
4. `uv run craft verify` で merge + veriq 検証
5. `uv run pytest -q` でテスト確認

### 新しい system を追加する

1. `uv run craft init system <name>` で雛形生成（`components.py` / `scope.py` / `data.toml`）
2. Component / Config / Analysis を実装
3. `uv run craft schema list` で registry に乗ったことを確認
4. `uv run craft verify` で end-to-end 確認

### Analysis（計算）を追加する

1. `systems/<sys>/analyses.py` に `@analysis(...)` 関数を追加
2. `uv run craft analysis list` で登録確認
3. `uv run craft analysis run <sys> <name>` で実行
