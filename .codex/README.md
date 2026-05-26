# .codex/

Codex CLI 固有の設定と運用メモ。

Codex をメインエージェントとして使う場合も、Claude Code と併用する場合も、共通ルールは以下を順に読む:

1. [`../AGENTS.md`](../AGENTS.md) — 全エージェント共通の作業ルール
2. [`../RULES.md`](../RULES.md) — Must Always / Must Never
3. [`../SOUL.md`](../SOUL.md) — 設計哲学
4. [`../.claude/rules/`](../.claude/rules/) — 詳細ルール（project / architecture / commands / git-workflow / security）

Claude Code は `@import` や hooks で自動化される部分があるが、Codex CLI では同じ機能が常に露出するとは限らない。必要に応じて明示的にファイルを読み、検証コマンドを実行する。

## Codex をメインにする場合

Codex は計画・実装・レビューのどれも担当できる。メインで使うときは以下を基本にする:

- 非自明な変更は、まず短い計画を提示してから実装する。
- 新機能・バグ修正では TDD を優先し、該当する `.claude/skills/<name>/SKILL.md` を必要に応じて読む。
- Claude Code hooks が動かない前提で、編集後は `just` や該当テストを明示的に実行する。
- MCP ツールが露出していない場合は、利用不可であることを明記し、`rg` / `rg --files` などで代替する。

## Claude Code と併用する場合

Claude Code から Codex に委譲する場合は、`.tasks/<name>.md` に意図・制約・検証方法を書いてから `just codex-run <name>` を使える。Codex の実行結果は、必要に応じて Claude Code 側でレビュー・統合する。

このフローは任意であり、Codex 単体で完結してもよい。

## 主要コマンド（justfile）

```bash
just codex-new-task <name>   # .tasks/<name>.md のテンプレを作る
just codex-run <name>        # .tasks/<name>.md を Codex に渡して実行
```

詳細は [`../justfile`](../justfile) を参照。

## モデル選択

`just codex-run` は `--model` 未指定。固定したい場合は justfile を編集するか直接 `node` を呼ぶこと。

## 守るべき制約

全エージェント共通の絶対遵守事項は [`../RULES.md`](../RULES.md) の Must Never を参照。

Codex 運用で追加で守る点:

- `.tasks/` のタスクファイルを一時作成した場合は、終了後に削除する（残骸禁止）。
- Claude Code 固有 hooks に依存せず、必要な検証を Codex 側でも明示的に実行する。
- CodeGraph MCP が使えないセッションでは、構造調査に `rg` / `rg --files` を使ってよい。
