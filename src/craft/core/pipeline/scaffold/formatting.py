"""Scaffold 出力 TOML テキストの空行・タイトル正規化。"""

import re


def normalize_scaffold_spacing(content: str) -> str:
    """scaffold 後の TOML テキストの空行を正規化する（冪等）。

    - `[...]` ヘッダ直前: 1 空行
    - MultiInstance のインスタンス切り替わり直前: 2 空行
    - `# === ... ===` 直前: 3 空行
    """
    content = re.sub(r"\n+(\[[^\]\n]+\])", lambda m: "\n\n" + m.group(1), content)
    content = _promote_instance_transitions(content)
    content = re.sub(r"\n+(# ===)", lambda m: "\n\n\n\n" + m.group(1), content)
    content = content.lstrip("\n")
    return content


def _promote_instance_transitions(content: str) -> str:
    """[root.A.x] → [root.B.y] の境界（インスタンス切り替わり）を 2 空行に昇格する。"""
    lines = content.split("\n")
    result: list[str] = []
    prev_instance: tuple[str, str] | None = None  # (root, instance)

    for line in lines:
        m = re.match(r"^\[([^\]]+)\]", line)
        if m:
            parts = m.group(1).split(".")
            if len(parts) >= 3:
                root, inst = parts[0], parts[1]
                if (
                    prev_instance is not None
                    and prev_instance[0] == root
                    and prev_instance[1] != inst
                ):
                    while result and result[-1] == "":
                        result.pop()
                    result.append("")
                    result.append("")
                prev_instance = (root, inst)
            else:
                prev_instance = None
        result.append(line)

    return "\n".join(result)


def class_name_to_title(cls: type) -> str:
    """CamelCase クラス名を単語スペース区切りに変換する。

    SunSenser → Sun Senser, OBC → OBC, MissionProfile → Mission Profile
    """
    name = cls.__name__
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return name
