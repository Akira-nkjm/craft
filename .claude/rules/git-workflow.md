# Git ワークフロー

> このリポジトリにおける Git 運用の**正典**。他ファイルからはここを参照する。

## コミットメッセージ（Conventional Commits）

```
<type>(<scope>): <概要（50文字以内）>

<本文（なぜを書く）>
```

- **type**: `feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `perf` / `ci`
- **scope**: 任意。変更範囲が明確なら付ける（例: `feat(hooks):`）
- **概要**: 現在形・命令形で 50 文字以内（"add" not "added"）
- **本文**: 任意。「何を」ではなく「なぜ」を書く

## ブランチ戦略

```
main          ← 常に動く状態を保つ
feature/<name>  ← 新機能
fix/<name>      ← バグ修正
chore/<name>    ← 設定・依存更新
```

- `main` への直接 push は禁止
- PR はレビュー後にマージ

## 禁止事項

絶対遵守事項は [`RULES.md`](../../RULES.md) の Must Never を参照。Git 関連の主な禁止:

- `git push --force` を `main` に対して実行しない
- `git commit --no-verify` でフックをスキップしない
- バイナリや生成ファイルをコミットしない（`.gitignore` で除外）

## よく使うコマンド

```bash
git status
git diff --staged          # コミット前の確認
git log --oneline -10      # 直近の履歴確認
git stash / git stash pop  # 作業の一時退避
```
