# AGENTS.md

このファイルは **AI エージェント全般**（Codex CLI / Claude Code / Cursor / OpenCode など）の統一ガイダンスです。

どのハーネスをメインにしても、このファイルを入口にして共通ルールを読む。Claude Code と Codex はどちらも主担当になれる前提で運用し、片方を「計画専用」「実装専用」に固定しない。

関連ドキュメント:

- [`RULES.md`](RULES.md) — Must Always / Must Never の絶対ルール
- [`SOUL.md`](SOUL.md) — 設計哲学と判断基準

ハーネス固有の設定は以下に分かれる:

- **共有ルール**: [`RULES.md`](RULES.md), [`SOUL.md`](SOUL.md), [`.claude/rules/`](.claude/rules/) — どちらのエージェントも尊重する
- **Claude Code 固有**: [`CLAUDE.md`](CLAUDE.md), [`.claude/`](.claude/) — imports, hooks, slash commands, Claude Code settings
- **Codex 固有**: [`.codex/`](.codex/) — Codex CLI での読み順、実行方法、制約

ハーネス固有機能（hooks、slash commands、MCP tool の露出など）は環境によって差が出る。使える場合は活用し、使えない場合は共通ルールに従って明示的なコマンド実行・ファイル確認・`rg` などで代替する。

---

## プロジェクト概要

詳細は [`.claude/rules/project.md`](.claude/rules/project.md) を参照。プロジェクト固有の情報（スタック・目的）はそこに書く。

## アーキテクチャ

詳細は [`.claude/rules/architecture.md`](.claude/rules/architecture.md) を参照。データフロー・モジュール構成・「なぜ」を書く。

## 開発コマンド

詳細は [`.claude/rules/commands.md`](.claude/rules/commands.md) を参照。セットアップ・テスト・ビルドの実コマンドを書く。

---

## 共通の作業ルール

### 1. 計画 → 承認 → 実装

非自明な変更は最初に計画を提示し、ユーザーの承認を得てから実装する。

### 2. テスト駆動（TDD）

新機能・バグ修正にはテストを書く。手順は [`tdd-workflow`](.claude/skills/tdd-workflow/SKILL.md) スキル参照。

### 3. イミュータビリティ

既存オブジェクトを変更せず、新しいオブジェクトを返す。

### 4. ファイル分割

- 高凝集・低結合、1 ファイル 200-400 行目安（最大 800）
- 関数 50 行以下、ネスト 4 段以下

### 5. エラーハンドリングとセキュリティ

- 境界（ユーザー入力・外部 API）では必ず検証
- 例外を握りつぶさない、文脈付きでログ
- セキュリティ規約は [`.claude/rules/security.md`](.claude/rules/security.md) 参照（正典）

### 6. コミット規約

[`.claude/rules/git-workflow.md`](.claude/rules/git-workflow.md) を参照（Conventional Commits）。

### 7. 禁止事項

[`RULES.md`](RULES.md) の Must Never を遵守。

---

## メインエージェント運用

Claude Code と Codex は、どちらをメインにしてもよい。

- **Claude Code メイン**: `CLAUDE.md` の imports / hooks / slash commands を活用しつつ、実装・調査・レビューを行う。必要に応じて `.tasks/` 経由で Codex に委譲する。
- **Codex メイン**: `AGENTS.md` → `RULES.md` → `SOUL.md` → `.claude/rules/*.md` の順に必要な範囲を明示的に読み、実装・調査・レビューを行う。Claude Code 固有 hooks が動かない場合は、`just` コマンドや該当テストを手動で実行して補う。
- **併用**: 一方が計画・実装・レビューのどれを担当してもよい。役割を固定せず、タスクのリスク・文脈量・利用可能ツールで決める。

## エージェント連携

標準的な連携例として **Claude（計画・レビュー）→ Codex（実装）→ Claude（統合・確認）** のフローを使える。これは必須ではない。詳細は [`.claude/rules/codex-workflow.md`](.claude/rules/codex-workflow.md) を参照（正典）。

Codex 単体で使う場合の運用は [`.codex/README.md`](.codex/README.md) を参照。

---

## 利用可能なスキル

Claude Code では `/skill-name` で起動可能。Codex 等の他ハーネスでは `.claude/skills/<name>/SKILL.md` を直接参照して同じ手順を適用する。

**いつどのスキルを使うか**（状況→スキルの早見表・トークン効率の読み方・codegraph の使い方）は [`.claude/rules/skills.md`](.claude/rules/skills.md) を参照（正典）。

- `tdd-workflow` — TDD（RED → GREEN → REFACTOR）の手順化
- `security-review` — OWASP・シークレット・入力検証チェック
- `strategic-compact` — コンテキスト圧縮戦略
- `deep-research` — 多ソース調査と引用付きレポート
- `documentation-lookup` — Context7 で最新ドキュメント取得
- `agent-introspection-debugging` — エージェントの自己デバッグ
- `eval-harness` — 出力評価ハーネス
- `coding-standards` — 命名・構造・コメント規約
- `api-design` — REST API 設計パターン
- `mcp-server-patterns` — MCP サーバ実装パターン
- `e2e-testing` — Playwright E2E パターン
- `find-skills` — スキル探索

## CodeGraph MCP

このリポジトリは [CodeGraph](https://github.com/colbymchenry/codegraph) MCP サーバを導入済み。`codegraph_*` MCP ツールが利用可能な環境では、コード構造に関する質問は **grep より先に CodeGraph** を使う:

- `codegraph_search` — シンボル検索
- `codegraph_callers` / `codegraph_callees` — 呼び出し関係
- `codegraph_explore` — 経路・フロー・概観・複数シンボルのソース一括（第一候補）
- `codegraph_impact` — 影響範囲
- `codegraph_node` / `codegraph_files` / `codegraph_status` — シンボル詳細 / ファイル一覧 / index 状態

CodeGraph が利用できない環境では、`rg` / `rg --files` を代替として使い、必要なら「このセッションでは CodeGraph MCP が露出していない」と明記する。ローカル完結・API キー不要。詳細は [`.claude/CLAUDE.md`](.claude/CLAUDE.md)。

## 参照ドキュメント

- [`.claude/docs/`](.claude/docs/) — 大きめのリファレンス資料
- [`.claude/instincts/`](.claude/instincts/) — 再利用可能な経験則
- [`README.md`](README.md) — リポジトリ概要・インストール手順
