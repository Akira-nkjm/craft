# プロジェクト固有の設定

<!-- このファイルをプロジェクトごとに編集する。CLAUDE.md は触らない。 -->

## プロジェクト概要

**Craft** — *Concept Registry for Automated spacecraFT design*。

宇宙機（衛星・深宇宙機を含む）の概念設計を **「型付き計算グラフ」** として宣言的に記述する基盤。
すべての定義を Pydantic 型で表現し、**CLI / FastAPI + Swagger UI / MCP（LLM agent）が同じ定義から
自動派生**する。データの検証・計算は姉妹ライブラリ **veriq** に委譲し、シームレスに統合する。

- ユーザが直接触るのは `systems/<name>/`（power / cdh / thermal / mission など）のみ。
  framework 実装は `src/craft/` 配下に隠す。
- 設計データは `systems/<name>/data.toml` に書き、`craft merge` で `generated/merged.toml` に
  統合され、veriq の入力になる。

技術スタック:

- 言語: **Python 3.14+**
- パッケージ管理・実行: **uv**（`uv sync` / `uv run`）
- 主要依存: `pydantic` / `fastapi` / `uvicorn` / `typer` / `mcp` / `tomlkit` / `tomli-w`、そして **`veriq`**

エントリポイント:

- `craft` — Typer CLI（`craft.cli.main:main`）
- `craft-mcp` — MCP サーバ（stdio, `craft.mcp_server.server:main`）
- FastAPI: `craft.api.main:app`（`uvicorn` で起動、Swagger UI は `/docs`）

## 規約・注意事項

- **single source of truth は Pydantic 定義**。CLI / API / MCP / JSON Schema はそこから派生させ、
  個別にスキーマを手書きしない。
- `data.toml` は簡略形式（`<sub>.model.` プレフィックス省略）で書き、`core.merge` が
  `generated/merged.toml` 生成時に補完する。`tomlkit` でコメントを保持する。
- framework（`src/craft/`）とユーザ領域（`systems/`）の境界を崩さない。
- 開発コマンドは uv 経由で実行する。グローバル `python` / `pip` を直接叩かない。
- `craft` は veriq に依存するが、veriq は craft に依存させない（依存方向を一方向に保つ）。

## 関連ドキュメント

- 開発コマンドは [`commands.md`](commands.md) に書く
- アーキテクチャと設計判断は [`architecture.md`](architecture.md) に書く
- 概念説明 [`docs/concepts.md`](../../docs/concepts.md) / チュートリアル [`docs/tutorial.md`](../../docs/tutorial.md)
- 目標アーキテクチャの正典: `plan/Craft/最終構成.md`
