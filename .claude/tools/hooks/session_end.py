#!/usr/bin/env python3
"""Stop / SessionEnd hook: セッション終了時に要約を保存する。

CLAUDE_SESSION_PERSIST=1 の場合のみ動作する。入力 JSON から transcript_path を取得し、最後のアシスタント発話 +
ファイル変更履歴を `.claude/sessions/<timestamp>.md` と `latest.md` に保存する。
保存前にメールアドレス、トークン風文字列、/Users/<name> などを redaction する。

ECC の session-end.js の Python 版（軽量）。

settings.local.json 例:
    {
      "Stop": [
        {"hooks": [{"type": "command",
                    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/tools/hooks/session_end.py"}]}
      ]
    }
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

HOOK_DIR = Path(__file__).parent
sys.path.insert(0, str(HOOK_DIR))
from _redact import redact_text  # noqa: E402

MAX_TRANSCRIPT_TAIL = 50  # 末尾何メッセージまで要約に使うか


def collect_summary(transcript_path: Path) -> tuple[str, list[str]]:
    """transcript JSONL から最後のアシスタント発話と編集ファイル一覧を抽出。"""
    last_assistant = ""
    touched_files: list[str] = []

    if not transcript_path.exists():
        return last_assistant, touched_files

    try:
        lines = transcript_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return last_assistant, touched_files

    for raw in lines[-MAX_TRANSCRIPT_TAIL * 4:]:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        # 最後のアシスタント発話を保持
        if msg.get("type") == "assistant":
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            if isinstance(content, str) and content.strip():
                last_assistant = redact_text(content)

        # tool_use の file_path を集める
        if msg.get("type") in {"assistant", "user"}:
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    file_path = (part.get("input") or {}).get("file_path")
                    if file_path and file_path not in touched_files:
                        touched_files.append(redact_text(file_path))

    return last_assistant, touched_files


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
    body = f"# Session {timestamp}\n\n"
    if touched_files:
        body += "## 編集されたファイル\n\n"
        for fp in touched_files[:30]:
            body += f"- {fp}\n"
        body += "\n"
    if last_assistant:
        body += "## 最終アシスタント発話\n\n"
        body += last_assistant[:4000].rstrip() + "\n"

    (sessions_dir / f"{timestamp}.md").write_text(body, encoding="utf-8")
    (sessions_dir / "latest.md").write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
