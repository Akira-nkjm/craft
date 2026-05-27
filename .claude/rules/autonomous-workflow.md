# 自律実装ワークフロー (Claude GitHub Action)

> このリポジトリでは `claude-implement` ラベルを Issue に付けると Claude が自動で実装 → PR 作成までやる。
> 実体は [`.github/workflows/claude.yml`](../../.github/workflows/claude.yml)。
> 設計の意図と落とし穴をここに残す（workflow ファイル内コメントの補完）。

## TL;DR

```bash
# 1 件実装
gh issue edit <N> --add-label claude-implement

# PR が立ったらレビューも自動 (手動コメント必要)
gh pr comment <PR#> --body "@claude review ..."

# マージ
gh pr merge <PR#> --merge   # branch は repo 設定で自動削除
```

## 全体フロー

```
Issue --label--> [Claude implements] --auto--> PR --@claude review--> [Claude reviews] --human--> merge
```

詳細:

1. **トリガー**: `claude-implement` ラベル または `@claude` メンション
2. **base 解決**: Issue body の `Base: #N` から前 PR の head ref を取得（ファスナー方式、後述）
3. **Claude 実装**: tag mode で issue body を user prompt として `anthropics/claude-code-action@v1` が動く
4. **Safety net**: 別ステップで branch を fresh checkout → `uv sync` → `just check` → `uv run pytest -q`
5. **Auto-PR**: safety net pass で `gh pr create`。body は `Closes #N` 付き、末尾スペース付加で issue link を強制再パース
6. **レビュー**: 人間が `@claude review` をコメント (`GITHUB_TOKEN` 由来の bot コメントは workflow 再起動しない GitHub 仕様のため)
7. **CI**: 通常の `ci.yml` が走る（ただし bot 作成 PR は close+reopen が必要なケースあり）
8. **マージ**: 人間判断で `gh pr merge`、branch は repo の `delete_branch_on_merge=true` で自動削除

## ラベル

| ラベル | 用途 |
|---|---|
| `claude-implement` | Issue に付与 → workflow が autonomous 実装を開始 |
| `claude-review` | （現在は使われていない / 旧設計の名残） |

## トリガー条件 (`if:` 句)

`claude.yml` の job-level `if:` は以下のいずれかで真:

- `issue_comment` で body に `@claude`
- `pull_request_review_comment` で body に `@claude`
- `pull_request_review` で review body に `@claude`
- `issues:labeled` で label が `claude-implement`
- `issues:opened` で body / title に `@claude`

## ファスナーチェーン (`Base: #N`)

依存ある Issue を **連鎖** で並行進行させる仕組み。

```
Issue body 冒頭に書く:
    Base: #65

Workflow が:
  - Issue #65 の open PR を gh で検索
  - その head ref (claude/issue-65-...) を取得
  - claude-code-action の base_branch input に渡す
  - 結果: 新 branch は前 PR の commits を内包した状態でスタート
```

効果:
- 5 PR を順次マージしてもファイル衝突ゼロ（各 PR の branch が前 PR の差分を持っているため、前 PR が main にマージされた時点で diff が当該分のみに自動縮小）

注意: 前 PR の open PR が存在することが前提。`Base: <branch-name>` 直書きも可。

## 認証

- **CLAUDE_CODE_OAUTH_TOKEN**: Claude Max サブスクの長寿命トークン（`claude setup-token` で発行）
- 追加 API 課金なし（Max のクオータ内で動く）
- 個人 PAT は使わない（GitHub の `GITHUB_TOKEN` で十分）

## Safety net の必要性

`anthropics/claude-code-action@v1` 単体だと:

- Claude が `just check` を**自分から**回さないことがある
- ruff format が空気を読まずに `except (A, B):` → `except A, B:` などを変えることがある
- pyrefly エラーや pytest 失敗があっても push してしまう

→ workflow に **safety net 専用ステップ** を入れて、push 済の branch を fresh checkout → 検証 → 失敗なら PR 作成スキップ。

実装メモ:
- Claude action が完了直後に走らせると **git credentials が clear されている** ので `git fetch` が 401。`actions/checkout@v4` を再度実行して認証復元する必要あり。

## ファイル変更が反映されない罠

- `--allowed-tools "..."` を `claude_args` で渡すと **action のデフォルト** (`Bash(git add)` / `Bash(git push.sh)` / `mcp__github_comment__update_claude_comment` 等) **が上書きで消える** → Claude が 27 ターン動いても push しないケース発生
- 解決: `claude_args` を **使わない**。tag mode (`prompt:` 入力なし) でデフォルトに任せる。安全網は workflow 側のステップで担保
- `prompt:` を渡すと issue body の自動ロード（tag mode）が無効化されて Claude が 1 ターンで終わる

## PR ↔ Issue の自動 link

- `Closes #N` を PR body に書けば原則自動 link されるが、**bot 作成 PR では稀に スキップされる**
- 対策: workflow で PR 作成直後に `gh pr edit <PR#> --body "${BODY} "` で末尾スペース付与 → GitHub が再パースして link 生成
- 結果は `gh pr view <PR#> --json closingIssuesReferences` で確認可能

## CI が走らない (bot PR の罠)

GitHub の **recursion guard**: `GITHUB_TOKEN` 由来のイベント（PR opened など）は `pull_request` トリガーの workflow を発火させない。

- **`@claude review` コメントの再帰**も同じ理由で発火しない（bot がコメントしても workflow は再起動しない）
- 対策:
  - CI: `close + reopen` する or 空コミット push（人間 or PAT 必要）
  - レビュー連鎖: 人間が `@claude review` をコメント

## トラブルシュート

| 症状 | 原因 | 対処 |
|---|---|---|
| Claude が turn 数稼ぐが push しない | `--allowed-tools` で git tools が落ちている | `claude_args` を空にする |
| Issue label 付けても workflow が走らない | action の内部 `label_trigger` が `claude` (デフォルト) | `label_trigger: claude-implement` を指定 |
| safety net で `git fetch` が 401 | Claude action が credentials を clean up | `actions/checkout@v4` で fresh checkout |
| `Closes #N` が link されない | bot PR 作成時に GitHub が再パースしないことがある | `gh pr edit --body "${BODY} "` で再保存 |
| `pull_request` workflow が bot PR で走らない | recursion guard | close+reopen or 空コミット |

## 認証関連の注意

- `CLAUDE_CODE_OAUTH_TOKEN` は Repo の Secrets に登録（`gh secret set CLAUDE_CODE_OAUTH_TOKEN`）
- 期限が来たら `claude setup-token` で再発行
- 漏洩しても repo に対する read/write のみで `GITHUB_TOKEN` の権限に縛られる

## 関連ファイル

- [`.github/workflows/claude.yml`](../../.github/workflows/claude.yml) — 本体
- [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) — PR の CI（lint / pyrefly / pytest / merge-check）
- [`.claude/rules/codex-workflow.md`](codex-workflow.md) — Codex への委譲手順（フォールバック用）
- [`justfile`](../../justfile) — `just check` の中身（safety net が呼ぶ）

## 歴史的経緯

本ワークフローは Issue #1 / #64 の自走実装中に試行錯誤で確立された。主な失敗と学び:

- 当初 `prompt:` 入力 + 独自 `--allowed-tools` で組んだら **push されないまま 54 turn 終了**事故
- `pull_request:labeled` + `track_progress: true` の組合せは **未対応イベント** (`labeled`) でエラー
- bot コメント由来の `issue_comment` イベントは **再発火しない** (recursion guard) → `@claude review` 自動 chain は不可
- `claude-review.yml` を別 workflow にしたが上記理由で動かず、`claude.yml` 一本化

詳細は当時の commit history 参照（`ci(claude): ...` プレフィックスのコミット群）。
