# CLAUDE.md

Claude Code 向けガイダンス。共通ルールは [`AGENTS.md`](AGENTS.md) を参照。

## 自動ロードされるルール (`.claude/rules/`)

- `project.md` — プロジェクト概要・スタック
- `architecture.md` — アーキテクチャ・データフロー・設計判断
- `commands.md` — セットアップ・テスト・ビルドコマンド
- `git-workflow.md` — コミットメッセージ規約・ブランチ戦略
- `codex-workflow.md` — Claude Code から Codex へ委譲する手順・並列実行・フォールバック
- `security.md` — セキュリティ規約・AgentShield 等の外部ツール
- `skills.md` - skillの使い所

## 利用可能なコマンド（`my-plugin` プラグイン提供）

コマンド・スキル・フック・MCP は `my-plugin` プラグインが提供する。プロジェクト内の `.claude/commands/` や `.claude/skills/` には**置かれない**（プラグインキャッシュ `~/.claude/plugins/cache/.../my-plugin/` に住み、そこから自動で効く）。

- `/setup-project [--force] [--no-codex]` — このルール一式・Codex 機械をプロジェクトに展開／更新する
- `/markitdown`（スキル） — Office/PDF/画像等を Markdown へ忠実変換（PDF の内容を読む・要約する場合もまずこれで変換する）

## 利用可能なスキル（`my-plugin` プラグイン提供）

Claude Code では `/skill-name` で起動できる。プラグインが提供するので、**プロジェクト内に `.claude/skills/` は存在しない**。Codex 等の他ハーネスで同じ手順を使う場合は、プラグインリポジトリ（`my-plugin/skills/<name>/SKILL.md`）を参照する。

- `find-skills` — インストール済みスキルの探索
- `markitdown` — ファイル → Markdown 変換（markitdown CLI）
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
| 「X から Y への経路・フロー」 | `codegraph_explore` |
| 「Z を変えると何が壊れる？」 | `codegraph_impact` |
| 「Y のシグネチャ/ソース」 | `codegraph_node` |
| 「ファイル構成・一覧」 | `codegraph_files` |
| 「複数シンボルのソース一括／概観」 | `codegraph_explore` |
| 「index は健康？」 | `codegraph_status` |

詳細な使い方ガイドは [`.claude/CLAUDE.md`](.claude/CLAUDE.md)（CodeGraph 公式の説明）を参照。

ルール: `codegraph_*` ツールが利用可能な環境では、**構造的な質問は grep より先に codegraph を使う**（高速・正確・トークン削減）。利用できない場合は `rg` / `rg --files` で代替する。

## メモリと学習

- **`.claude/sessions/`** — `session_start` / `session_end` / `pre_compact` フックが自動保存（フックは `my-plugin` 提供。`CLAUDE_SESSION_PERSIST=1` の時だけ動作。`.claude/sessions/` は git 管理外に）
- **`.claude/instincts/`** — 再利用可能な経験則（YAML）。使う場合のみ作成する

## Codex 連携ワークフロー

正典: [`.claude/rules/codex-workflow.md`](.claude/rules/codex-workflow.md)。Claude Code をメインにする場合は、必要に応じて **計画 → 承認 → Codex 委譲** の流れを使える。Codex をメインにする場合は [`.codex/README.md`](.codex/README.md) を入口にし、共通ルールは `AGENTS.md` / `RULES.md` / `SOUL.md` / `.claude/rules/` を参照する。

## 参照ドキュメント (`.claude/docs/`)

大きめのリファレンスはプロジェクトで必要になったら `.claude/docs/` に置き、`@.claude/docs/<file>.md` で参照する（既定では存在しない）。

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
@.claude/rules/skills.md
