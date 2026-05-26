#!/usr/bin/env python3
"""PreToolUse hook: block agent edits to Claude settings files."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def protected_paths() -> set[Path]:
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    home = Path.home().resolve()
    return {
        (project_dir / ".claude" / "settings.json").resolve(),
        (project_dir / ".claude" / "settings.local.json").resolve(),
        (home / ".claude" / "settings.json").resolve(),
    }


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        warn(f"hook input JSON parse error: {e}. hook を skip します")
        return 0

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return 0

    candidate = Path(file_path).expanduser()
    if not candidate.is_absolute():
        candidate = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / candidate
    candidate = candidate.resolve()

    if candidate in protected_paths():
        warn(f"⛔ 設定ファイル ({candidate}) の直接編集はブロックされています。")
        warn("変更が必要な場合はユーザーが直接編集してください。")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
