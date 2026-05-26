default:
    @just --list

# プロジェクトルート（親ディレクトリ）に非破壊でインストールする
# 使い方: プロジェクト配下に git clone してから just install
# FORCE=1 で既存ファイルをバックアップ後に上書き、DRY_RUN=1 で差分のみ表示
install:
    @python3 .claude/tools/install/install.py

# Codex にタスクファイルを渡して実行する
# 使い方: just codex-run <task-name>  (.tasks/<task-name>.md を渡す)
codex-run name:
    @python3 .claude/tools/codex/run.py "{{ name }}"

# タスクファイルを新規作成する
# 使い方: just codex-new-task <task-name>
# FORCE=1 で既存 .tasks/<task-name>.md の上書きを許可
codex-new-task name:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .tasks
    task=".tasks/{{ name }}.md"
    if [ -e "$task" ] && [ "${FORCE:-0}" != "1" ]; then
        echo "Task already exists: $task (set FORCE=1 to overwrite)" >&2
        exit 1
    fi
    printf "# {{ name }}\n\n## 概要\n\n## 実装方針\n\n## 注意事項\n" > "$task"
    echo "Created: $task"

# 未処理タスク一覧
codex-tasks:
    @ls .tasks/*.md 2>/dev/null || echo "no task"

# Codex を git worktree 隔離で実行する（並列実行時に推奨）
# worktree: .worktrees/<task-name>/、branch: codex/<task-name>
# 使い方: just codex-run-isolated <task-name>
codex-run-isolated name:
    #!/usr/bin/env bash
    set -euo pipefail
    task=".tasks/{{ name }}.md"
    if [ ! -f "$task" ]; then
        echo "タスクファイルが見つかりません: $task" >&2
        exit 1
    fi
    wt=".worktrees/{{ name }}"
    branch="codex/{{ name }}"
    if [ ! -d "$wt" ]; then
        git worktree add -b "$branch" "$wt" HEAD
    fi
    mkdir -p "$wt/.tasks"
    cp "$task" "$wt/$task"
    (cd "$wt" && python3 .claude/tools/codex/run.py "{{ name }}")
    echo "完了: $wt (branch: $branch)"
    echo "マージ例: git merge --no-ff $branch  または  cd $wt && git diff main"
    echo "破棄例:   just codex-cleanup-isolated {{ name }}"

# worktree とブランチを削除する
# 使い方: just codex-cleanup-isolated <task-name>
codex-cleanup-isolated name:
    #!/usr/bin/env bash
    set -euo pipefail
    wt=".worktrees/{{ name }}"
    branch="codex/{{ name }}"
    if [ -d "$wt" ]; then
        git worktree remove --force "$wt"
    fi
    git branch -D "$branch" 2>/dev/null || true
    echo "削除: $wt, $branch"

# CodeGraph index を作成・再構築する（初回または手動再構築時）
# 通常はファイル監視で自動更新されるので不要
codegraph-init:
    npx -y @colbymchenry/codegraph init -i

# CodeGraph の健康確認
codegraph-status:
    npx -y @colbymchenry/codegraph status
