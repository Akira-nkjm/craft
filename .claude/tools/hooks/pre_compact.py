#!/usr/bin/env python3
"""PreCompact hook: コンテキスト圧縮の直前にスナップショットを保存する。

CLAUDE_SESSION_PERSIST=1 の場合のみ動作する。session_end.py と同じ要約ロジックを使い、
`.claude/sessions/pre-compact-<ts>.md` に保存。
圧縮で失われる情報を後から復元できるようにする保険。

settings.local.json 例:
    {
      "PreCompact": [
        {"hooks": [{"type": "command",
                    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/tools/hooks/pre_compact.py"}]}
      ]
    }
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# session_end と同じロジックを再利用
HOOK_DIR = Path(__file__).parent
sys.path.insert(0, str(HOOK_DIR))
from session_end import collect_summary  # noqa: E402


def main() -> int:
    if os.environ.get("CLAUDE_SESSION_PERSIST") != "1":
        return 0

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"hook input JSON parse error: {e}. hook を skip します", file=sys.stderr)
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    sessions_dir = project_dir / ".claude" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    transcript_path_str = data.get("transcript_path") or ""
    last_assistant, touched_files = collect_summary(Path(transcript_path_str))

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    body = f"# Pre-Compact Snapshot {timestamp}\n\n"
    if touched_files:
        body += "## 編集されたファイル\n\n"
        for fp in touched_files[:50]:
            body += f"- {fp}\n"
        body += "\n"
    if last_assistant:
        body += "## 圧縮直前のアシスタント発話\n\n"
        body += last_assistant[:6000].rstrip() + "\n"

    (sessions_dir / f"pre-compact-{timestamp}.md").write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
