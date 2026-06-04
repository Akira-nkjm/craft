# craft プロジェクトの justfile
#
# Codex 連携・CodeGraph レシピは `.claude/justfile`（プラグイン提供の正典）を import する。
# これにより `just codex-run <task>` / `just codegraph-status` などが直接（補完付きで）使える。
# 正典側は task name を quote() + 検証してシェルへ渡す（injection / path traversal 対策）ので、
# ここで重複定義はしない。
import '.claude/justfile'

# import 元（.claude/justfile）の `default` をこのファイルの `default` で上書きする。
# 後勝ちにするため allow-duplicate-recipes を有効化（衝突するのは default のみ）。
set allow-duplicate-recipes := true

default:
    @just --list

# --- 依存・実行 ---

# 依存をインストール（dev グループ含む）
sync:
    uv sync

# FastAPI を起動する（Swagger UI: http://localhost:8000/docs）
# PORT=N で port 上書き可
api:
    uv run uvicorn craft.api.main:app --reload --port {{ env_var_or_default("PORT", "8000") }}

# craft-mcp を起動する（stdio MCP サーバ）
craft-mcp:
    uv run craft-mcp

# --- コード品質 ---

# ruff で format 実行
fmt:
    uv run ruff format .

# ruff format の差分チェックのみ（CI 用）
fmt-check:
    uv run ruff format --check .

# ruff で lint 実行
lint:
    uv run ruff check .

# ruff で lint 自動修正
lint-fix:
    uv run ruff check --fix .

# pyrefly で型チェック
typecheck:
    uv run pyrefly check

# 全テスト
test:
    uv run pytest .

# format + lint-fix + typecheck + test をまとめて実行
check: fmt lint-fix typecheck test
