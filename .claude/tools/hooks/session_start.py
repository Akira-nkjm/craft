#!/usr/bin/env python3
"""SessionStart hook: 直近のセッション要約を読み込んで context として返す。

ECC の memory-persistence パターンの最小実装。

挙動:
  - CLAUDE_SESSION_PERSIST=1 の場合のみ動作する
  - $CLAUDE_PROJECT_DIR/.claude/sessions/latest.md があれば、その内容を additionalContext として返す
  - サイズは ECC_SESSION_START_MAX_CHARS で制限 (デフォルト 8000)

settings.local.json 例:
    {
      "SessionStart": [
        {"hooks": [{"type": "command",
                    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/tools/hooks/session_start.py"}]}
      ]
    }
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    if os.environ.get("CLAUDE_SESSION_PERSIST") != "1":
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    latest = Path(project_dir) / ".claude" / "sessions" / "latest.md"
    if not latest.exists():
        return 0

    try:
        max_chars = int(os.environ.get("ECC_SESSION_START_MAX_CHARS", "8000"))
    except ValueError:
        max_chars = 8000

    try:
        content = latest.read_text(encoding="utf-8")
    except OSError as e:
        print(f"session_start: 読み込み失敗: {e}", file=sys.stderr)
        return 0

    if len(content) > max_chars:
        content = content[-max_chars:]
        content = "...(古い部分を省略)...\n" + content

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"## 前回セッションの要約\n\n{content}",
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
