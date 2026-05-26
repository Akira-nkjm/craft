#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def last_error_line(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip()
    return text.splitlines()[-1] if text else "no error output"


def run_formatter(name: str, command: list[str], file_path: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ {name}: {os.path.basename(file_path)}")
    else:
        warn(f"{name} failed: {last_error_line(result)}. 手動実行: {' '.join(command)}")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        warn(f"hook input JSON parse error: {e}. hook を skip します")
        return 0

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return 0

    if file_path.endswith(".py") and shutil.which("uv"):
        run_formatter("ruff format", ["uv", "run", "ruff", "format", file_path], file_path)
    elif file_path.endswith((".js", ".ts", ".tsx", ".jsx")) and shutil.which("pnpm"):
        run_formatter("prettier", ["pnpm", "exec", "prettier", "--write", file_path], file_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
