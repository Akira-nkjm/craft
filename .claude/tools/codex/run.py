#!/usr/bin/env python3
"""Run a .tasks/<name>.md task through the Codex companion plugin.

The canonical entrypoint is the Claude plugin cache script:
  ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


PLUGIN_GLOB = "~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs"

# task name は .tasks/<name>.md に展開されるため、path traversal・シェルメタ文字を禁止する
TASK_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def version_key(path: Path) -> tuple[tuple[int, ...], str]:
    version = path.parent.parent.name
    parts = re.split(r"[.+-]", version)
    nums: list[int] = []
    suffix: list[str] = []
    for part in parts:
        if part.isdigit() and not suffix:
            nums.append(int(part))
        else:
            suffix.append(part)
    return tuple(nums), ".".join(suffix)


def find_companion() -> Path:
    matches = [Path(p) for p in glob.glob(os.path.expanduser(PLUGIN_GLOB))]
    if not matches:
        print("Codex plugin がインストールされていません。`/codex:setup` を実行してください。", file=sys.stderr)
        raise SystemExit(1)
    selected = sorted(matches, key=version_key)[-1]
    if len(matches) > 1:
        print(f"Codex companion: {selected}", file=sys.stderr)
    return selected


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: run.py <task-name>", file=sys.stderr)
        return 2
    if not shutil.which("node"):
        print("node が PATH にありません。Node.js をインストールしてから再実行してください。", file=sys.stderr)
        return 1

    task_name = argv[1]
    if not TASK_NAME_RE.match(task_name) or ".." in task_name:
        print(f"不正なタスク名: {task_name}（英数字 . _ - のみ、.. 不可）", file=sys.stderr)
        return 2
    prompt_file = Path(".tasks") / f"{task_name}.md"
    if not prompt_file.exists():
        print(f"タスクファイルが見つかりません: {prompt_file}", file=sys.stderr)
        return 1

    companion = find_companion()
    cmd = ["node", str(companion), "task", "--write", "--prompt-file", str(prompt_file)]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
