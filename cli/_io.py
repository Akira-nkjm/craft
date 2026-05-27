import json
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from core.serialization import to_jsonable


def _print_json(obj: Any) -> None:
    typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=to_jsonable))


def _load_payload(data_path: Path | None, json_str: str | None) -> dict[str, Any]:
    """`--data <path>` (TOML/JSON) または `--json <str>` または stdin から payload を読む。"""
    if data_path is not None and json_str is not None:
        raise typer.BadParameter("--data と --json は同時に指定できません")
    if data_path is not None:
        if not data_path.exists():
            raise typer.BadParameter(f"file not found: {data_path}")
        suffix = data_path.suffix.lower()
        if suffix == ".toml":
            from core.toml_io import read_toml

            return read_toml(data_path)
        if suffix == ".json":
            return _parse_json_strict(data_path.read_text(encoding="utf-8"), source=str(data_path))
        raise typer.BadParameter(f"unsupported extension: {suffix} (expected .toml or .json)")
    if json_str is not None:
        return _parse_json_strict(json_str, source="--json")
    raw = sys.stdin.read()
    if not raw.strip():
        raise typer.BadParameter("payload が空です（--data / --json / stdin のいずれかを指定）")
    return _parse_json_strict(raw, source="stdin")


def _parse_json_strict(raw: str, *, source: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"{source} の JSON 解析に失敗: {e}") from e
    if not isinstance(obj, dict):
        raise typer.BadParameter(f"{source} の payload は object である必要があります")
    return obj


def _format_validation_error(err: ValidationError) -> str:
    lines = ["ValidationError:"]
    for e in err.errors():
        loc = ".".join(str(p) for p in e.get("loc", ()))
        msg = e.get("msg", "")
        lines.append(f"  - {loc}: {msg}")
    return "\n".join(lines)
