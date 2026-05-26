# CLAUDE.md

Claude Code 向けガイダンス。共通ルールは [`AGENTS.md`](AGENTS.md) を参照。

## 自動ロードされるルール (`.claude/rules/`)

- `project.md` — プロジェクト概要・スタック
- `architecture.md` — アーキテクチャ・データフロー・設計判断
- `commands.md` — セットアップ・テスト・ビルドコマンド
- `git-workflow.md` — コミットメッセージ規約・ブランチ戦略
- `codex-workflow.md` — Claude Code から Codex へ委譲する手順・並列実行・フォールバック
- `security.md` — セキュリティ規約・AgentShield 等の外部ツール

## 利用可能なコマンド (`.claude/commands/`)

- `/read-pdf <path> [--pages N] [--interval N]` — PDF をページごとに読み込み Markdown サマリーを生成。出力先: `book_analysis/`

## 利用可能なスキル (`.claude/skills/`)

Claude Code では `/skill-name` で起動できる。他ハーネスで同じ手順を使う場合は、該当する `.claude/skills/<name>/SKILL.md` を直接参照する。

- `find-skills` — インストール済みスキルの探索
- `tdd-workflow` / `security-review` / `strategic-compact` / `deep-research` / `documentation-lookup`
- `agent-introspection-debugging` / `eval-harness` / `coding-standards` / `api-design` / `mcp-server-patterns` / `e2e-testing`

## CodeGraph MCP

このリポジトリは [CodeGraph](https://github.com/colbymchenry/codegraph) を導入済み。MCP サーバ経由でコード構造を query できる（**API キー不要・ローカル完結**）。

主な MCP ツール:

| 質問 | ツール |
|---|---|
| 「X はどこで定義？」「シンボル X 検索」 | `codegraph_search` |
| 「Y を呼ぶのは？」 | `codegraph_callers` |
| 「Y は何を呼ぶ？」 | `codegraph_callees` |
| 「X から Y への経路」 | `codegraph_trace` |
| 「Z を変えると何が壊れる？」 | `codegraph_impact` |
| 「Y のシグネチャ/ソース」 | `codegraph_node` |
| 「タスク用の context」 | `codegraph_context` |
| 「複数シンボルのソース一括」 | `codegraph_explore` |
| 「index は健康？」 | `codegraph_status` |

詳細な使い方ガイドは [`.claude/CLAUDE.md`](.claude/CLAUDE.md)（CodeGraph 公式の説明）を参照。

ルール: `codegraph_*` ツールが利用可能な環境では、**構造的な質問は grep より先に codegraph を使う**（高速・正確・トークン削減）。利用できない場合は `rg` / `rg --files` で代替する。

## メモリと学習

- **`.claude/sessions/`** — `session_start.py` / `session_end.py` / `pre_compact.py` フックが自動保存（要 settings.local.json 登録）
- **`.claude/instincts/`** — 再利用可能な経験則（YAML）。詳細は `.claude/instincts/README.md`

## Codex 連携ワークフロー

正典: [`.claude/rules/codex-workflow.md`](.claude/rules/codex-workflow.md)。Claude Code をメインにする場合は、必要に応じて **計画 → 承認 → Codex 委譲** の流れを使える。Codex をメインにする場合は [`.codex/README.md`](.codex/README.md) を入口にし、共通ルールは `AGENTS.md` / `RULES.md` / `SOUL.md` / `.claude/rules/` を参照する。

## 参照ドキュメント (`.claude/docs/`)

大きめのリファレンスは `.claude/docs/` に置き、必要時に `@.claude/docs/<file>.md` で参照する。

---

@AGENTS.md
@RULES.md
@SOUL.md
@.claude/rules/project.md
@.claude/rules/architecture.md
@.claude/rules/commands.md
@.claude/rules/git-workflow.md
@.claude/rules/codex-workflow.md
@.claude/rules/security.md
