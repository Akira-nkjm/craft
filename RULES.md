# RULES

このリポジトリで作業する全エージェントが遵守すべきルール。詳細な作業手順は [`AGENTS.md`](AGENTS.md)、ファイル/設定の役割は [`README.md`](README.md) を参照。

## Must Always（必ず守る）

- **計画 → 承認 → 実装** の順で進める（自明な小変更を除く）
- テストを先に書き、重要パスは実行して確認する（手順は [`tdd-workflow`](.claude/skills/tdd-workflow/SKILL.md) スキル）
- 入力検証とセキュリティチェックを残す
- 共有状態の変更ではなく、イミュータブルな更新を選ぶ
- 既存の規約・パターンを優先する（独自発明より先に既存を探す）
- 変更は小さく、レビュー可能な単位に保つ
- リポジトリのルール（`.claude/rules/*.md`）を読み、それに従う

## Must Never（絶対にしない）

- シークレット（API キー、トークン、絶対パス、個人情報）を出力に含めない
- テスト未実行の変更をコミット・プッシュしない
- セキュリティチェック・検証フックをバイパスしない（`--no-verify` 禁止）
- 既存機能を理由なく重複実装しない
- `main` ブランチへの直接 push / force push をしない
- ユーザーの承認なしに破壊的操作（`rm -rf`、`git reset --hard`、`drop table`）を行わない

## Agent フォーマット（任意・追加する場合）

カスタムサブエージェントを足すときの規約。本リポジトリには現時点で同梱なし。

- エージェントは `.claude/agents/*.md` に配置
- YAML フロントマターに `name` / `description` / `tools` / `model` を含める
- ファイル名は小文字ハイフン、`name` と一致させる
- description は「いつ呼び出すべきか」を明確に書く

## Skill フォーマット

- スキルは `.claude/skills/<name>/SKILL.md` に配置
- YAML フロントマターに `name` / `description` / `origin` を含める
- `origin: local` を first-party（このリポジトリ起源）、`origin: community` を外部由来に使う
- 本文には「When to Use」セクション、実例、テスト済みコマンドを含める

## Hook フォーマット

- フックは `matcher`（`Edit|Write`、`Bash` など）で範囲を絞り、catch-all を避ける
- ブロックが意図的な場合のみ exit 2 を返す。それ以外は exit 0
- エラー／情報メッセージは**実行可能（actionable）**にする（「何をすればよいか」を書く）
- フックスクリプトのパスは `$CLAUDE_PROJECT_DIR/.claude/tools/hooks/...` のように絶対化する

## Commit Style

詳細は [`.claude/rules/git-workflow.md`](.claude/rules/git-workflow.md) を参照（正典）。

- Conventional Commits 形式
- 命令形・現在形・50 文字以内
- 本文には「なぜ」を書く
- PR 説明にユーザー影響を明記する
