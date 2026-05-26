# 開発コマンドリファレンス

> Craft で実際に動くコマンド。新しいコマンドを足したら更新する（陳腐化防止）。

## セットアップ

```bash
uv sync                                  # 依存解決（dev グループ含む）
```

Python 3.14 以上が必要。`uv` 未導入なら <https://docs.astral.sh/uv/> を参照。

## 実行

```bash
uv run uvicorn api.main:app --reload     # FastAPI (http://127.0.0.1:8000/docs)
uv run craft-mcp                         # MCP サーバ (stdio)
uv run craft <command>                   # CLI（下記参照）
```

## テスト

```bash
uv run pytest                            # 全テスト
uv run pytest tests/test_X.py            # 単一ファイル
uv run pytest -q                         # 簡潔出力（CI と同じ）
```

## コード品質

```bash
uv run ruff check .                      # Lint
uv run ruff check --fix .                # 自動修正
uv run ruff format .                     # フォーマット
uv run pyrefly check                     # 型チェック
```

## 主要 CLI コマンド

```bash
uv run craft --help                                 # ヘルプ
uv run craft schema list                            # 登録済み subsystem / component
uv run craft schema show <sub> <comp>               # JSON Schema
uv run craft get <sub> <comp> [<inst>]              # インスタンス取得
uv run craft merge [--check] [--dry-run]            # data.toml → merged.toml
uv run craft scaffold [<sub>] [--dry-run]           # registry → data.toml 雛形
uv run craft verify [--no-fail-on-verify]           # merge → veriq evaluate
uv run craft analysis list                          # @analysis 一覧
uv run craft analysis run <sub|_> <name> [--payload JSON]
uv run craft init subsystem <name> [--kind hardware|config-only|default]
```

## CI と同等のローカル実行

GitHub Actions (`.github/workflows/ci.yml`) と同じ順で確認したい場合:

```bash
uv run ruff check .
uv run pyrefly check
uv run pytest -q
uv run craft merge --check
```

## その他のタスク

`justfile` に補助タスクがある（`just --list` で一覧）:

```bash
just sync                                # uv sync
just fmt / fmt-check                     # ruff format
just lint / lint-fix                     # ruff check
just typecheck                           # pyrefly
just check                               # fmt + lint-fix + typecheck をまとめて
just codegraph-init                      # CodeGraph index 再構築
just codegraph-status                    # CodeGraph 健康確認
```
