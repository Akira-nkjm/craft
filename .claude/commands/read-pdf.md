---
name: read-pdf
description: PDF をページごとに読み込み、知識ポイントを抽出して Markdown サマリーを生成する
---

## When to Activate

ユーザーが PDF ファイルの内容を要約・分析したいとき。`/read-pdf <path>` と呼び出す。

## 使い方

```bash
uv run python .claude/tools/read_pdf.py <PDFのパス> [--pages N] [--interval N] [--backend api]
```

- `--pages N` — 処理するページ数の上限（省略時は全ページ）
- `--interval N` — N ページごとに中間サマリーを生成
- `--backend api` — Anthropic API を使う（デフォルトは `claude-cli`）

## 出力先

- `book_analysis/knowledge_bases/<stem>_knowledge.json` — 抽出した知識ポイント（中断・再開可能）
- `book_analysis/summaries/<stem>_final_001.md` — 最終 Markdown サマリー
- `book_analysis/summaries/<stem>_interval_*.md` — 中間サマリー

## Anti-patterns

- 大きい PDF を `--pages` なしで実行しない（タイムアウトする）
- `--backend api` は API キーが必要なため、デフォルトの `claude-cli` を優先する
