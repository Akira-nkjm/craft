#!/usr/bin/env python3
"""PreToolUse hook: 危険な Bash コマンドをブロックする。

settings.local.json 例:
    {"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/tools/hooks/dangerous_cmd.py"}
"""
import json
import re
import sys


def warn(msg: str) -> None:
    print(msg, file=sys.stderr)


# 危険コマンドのパターン。各タプルは (正規表現, 説明)
DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "コミット履歴の強制リセット"),
    (re.compile(r"\bgit\s+push\s+(?:--force\b|-f\b|--force-with-lease\b)"), "リモートへの強制プッシュ"),
    (re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f"), "未追跡ファイルの強制削除"),
    (re.compile(r"\bgit\s+checkout\s+--\s"), "ファイルの強制上書き"),
    (re.compile(r"\bgit\s+branch\s+-D\b"), "ブランチの強制削除"),
    (re.compile(r"\b(?:sudo\s+)?(?:dd|mkfs|fdisk)\b"), "ディスク操作系コマンド"),
    (re.compile(r":\(\)\s*\{.*\|.*&\s*\}"), "フォーク爆弾の疑い"),
    (re.compile(r"\bchmod\s+-R\s+777\b"), "再帰的な 777 パーミッション"),
    (re.compile(r"\bcurl\s+[^|]*\|\s*(?:sudo\s+)?(?:bash|sh|zsh)\b"), "curl パイプ実行 (任意コード実行)"),
    (re.compile(r"\bwget\s+[^|]*\|\s*(?:sudo\s+)?(?:bash|sh|zsh)\b"), "wget パイプ実行 (任意コード実行)"),
]

# rm に対する特に危険な対象（ブロック対象がパターン本体と重なる場合の追加警告）
RM_CRITICAL_TARGETS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brm\s+(?:-\S+\s+)*/\s*(?:$|;|&)"), "ルートディレクトリ (/) への rm"),
    (re.compile(r"\brm\s+(?:-\S+\s+)*~(?:/|\s|$)"), "ホームディレクトリ全体への rm"),
    (re.compile(r"\brm\s+(?:-\S+\s+)*\$HOME(?:/|\s|$)"), "$HOME 全体への rm"),
    (re.compile(r"\brm\s+(?:-\S+\s+)*[^\s]*\.ssh(?:/|\s|$)"), ".ssh ディレクトリへの rm"),
    (re.compile(r"\brm\s+(?:-\S+\s+)*[^\s]*\.git(?:/|\s|$)"), ".git ディレクトリへの rm"),
]

RM_COMMAND = re.compile(r"(?<![\w-])rm\s+((?:-[^\s]+\s+)*)")


def has_recursive_force_rm(command: str) -> bool:
    """Return True only for rm invocations combining -r/-R and -f."""
    for match in RM_COMMAND.finditer(command):
        flags = match.group(1).split()
        has_recursive = any(("r" in flag or "R" in flag) for flag in flags if flag != "--")
        has_force = any("f" in flag for flag in flags if flag != "--")
        if has_recursive and has_force:
            return True
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        warn(f"hook input JSON parse error: {e}. hook を skip します")
        return 0

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return 0

    if has_recursive_force_rm(command):
        warn("⚠️ 危険なコマンドを検知: ディレクトリの強制削除 (rm -rf 系)")
        warn(f"   コマンド: {command}")
        for target_pat, target_desc in RM_CRITICAL_TARGETS:
            if target_pat.search(command):
                warn(f"🚨 さらに重大: {target_desc}")
                break
        warn("意図的な場合はターミナルから直接実行してください。")
        return 2

    for pattern, description in DANGEROUS_PATTERNS:
        if pattern.search(command):
            warn(f"⚠️ 危険なコマンドを検知: {description}")
            warn(f"   コマンド: {command}")
            warn("意図的な場合はターミナルから直接実行してください。")
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
