# 開発コマンドリファレンス

> プロジェクトごとに編集するテンプレート。実際に動くコマンドだけを書く（陳腐化防止）。

## セットアップ

```bash
# 依存インストール（ロックファイルから同期）。Python 3.14+ が必要
uv sync
```

## 実行

```bash
uv run craft --help                                  # CLI ヘルプ
uv run craft schema list                             # 登録済み system / component 一覧
uv run craft verify                                  # merge + veriq による検証実行
uv run uvicorn craft.api.main:app --reload           # FastAPI 起動 (Swagger UI: http://localhost:8000/docs)
uv run craft-mcp                                      # MCP サーバ (stdio) — Claude Code / Desktop から利用
```

主な CLI サブコマンド:

```bash
uv run craft schema show <sub> <comp>       # JSON Schema 表示
uv run craft get <sub> <comp> [<inst>]      # インスタンス取得
uv run craft merge [--check] [--dry-run]    # data.toml → generated/merged.toml
uv run craft scaffold [<sub>] [--dry-run]   # data.toml 雛形生成
uv run craft analysis list                  # @analysis 一覧
uv run craft analysis run <sub> <name>      # @analysis 実行
uv run craft init system <name>             # system 雛形生成
```

## テスト

```bash
uv run pytest                      # 全テスト
uv run pytest tests/craft          # 特定ディレクトリ
uv run pytest -k <keyword>         # 名前フィルタ
```

## コード品質

```bash
uv run ruff check .                # Lint
uv run ruff check . --fix          # 自動修正
uv run ruff format .               # フォーマット
uv run pyrefly check               # 型チェック
```

## ビルド / リリース

```bash
uv build                           # wheel / sdist をビルド (hatchling)
```

## その他のタスク

```bash
# Codex 連携（プラグインの機械）。詳細は .codex/README.md
just -f .claude/justfile codex-run <task-name>

# ドキュメント（Zensical）。設定は zensical.toml
```
