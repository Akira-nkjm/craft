"""既存の justfile に新しいレシピだけをマージする。"""
import re
import sys

src = open("justfile", encoding="utf-8").read()
dst_path = sys.argv[1]
dst = open(dst_path, encoding="utf-8").read()

blocks = re.split(r"\n{2,}", src.strip())
to_append = []
skipped = []


def recipe_name(block):
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z][a-zA-Z0-9_-]*)", stripped)
        return m.group(1) if m else None
    return None


for block in blocks:
    name = recipe_name(block)
    if not name:
        continue
    if re.search(r"^" + re.escape(name) + r"[\s:]", dst, re.MULTILINE):
        skipped.append(name)
    else:
        to_append.append(block)

if to_append:
    with open(dst_path, "a", encoding="utf-8") as f:
        f.write("\n\n" + "\n\n".join(to_append) + "\n")
    print("Merged", len(to_append), "recipe(s) into justfile")
else:
    print("justfile up to date")

if skipped:
    print("以下の recipe は既存と重複するため追加されませんでした: " + ", ".join(skipped))
