"""core/atomic_write のユニットテスト。interruption simulation を含む。"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.atomic_write import atomic_write_bytes, atomic_write_json, atomic_write_text


def test_atomic_write_bytes_creates_file(tmp_path: Path) -> None:
    p = tmp_path / "test.bin"
    atomic_write_bytes(p, b"hello")
    assert p.read_bytes() == b"hello"


def test_atomic_write_text_creates_file(tmp_path: Path) -> None:
    p = tmp_path / "test.txt"
    atomic_write_text(p, "こんにちは")
    assert p.read_text(encoding="utf-8") == "こんにちは"


def test_atomic_write_json_creates_file(tmp_path: Path) -> None:
    p = tmp_path / "test.json"
    atomic_write_json(p, {"key": "value"})
    assert json.loads(p.read_text(encoding="utf-8")) == {"key": "value"}


def test_atomic_write_creates_parent_dirs(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "deep" / "test.txt"
    atomic_write_text(p, "content")
    assert p.read_text(encoding="utf-8") == "content"


def test_atomic_write_overwrites_existing(tmp_path: Path) -> None:
    p = tmp_path / "test.txt"
    p.write_text("old content", encoding="utf-8")
    atomic_write_text(p, "new content")
    assert p.read_text(encoding="utf-8") == "new content"


def test_atomic_write_no_temp_files_remain_on_success(tmp_path: Path) -> None:
    p = tmp_path / "test.txt"
    atomic_write_text(p, "content")
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_bytes_cleans_temp_on_error(tmp_path: Path) -> None:
    """Interruption simulation: os.replace fails — original is preserved, temp is cleaned up."""
    p = tmp_path / "test.bin"
    p.write_bytes(b"original")

    with patch("core.atomic_write.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            atomic_write_bytes(p, b"new content")

    assert p.read_bytes() == b"original"
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_text_cleans_temp_on_error(tmp_path: Path) -> None:
    """Interruption simulation: os.replace fails — original is preserved, temp is cleaned up."""
    p = tmp_path / "test.txt"
    p.write_text("original", encoding="utf-8")

    with patch("core.atomic_write.os.replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            atomic_write_text(p, "new content")

    assert p.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_write_json_indent(tmp_path: Path) -> None:
    p = tmp_path / "test.json"
    atomic_write_json(p, {"a": 1}, indent=4)
    text = p.read_text(encoding="utf-8")
    assert '    "a"' in text


def test_atomic_write_json_no_indent(tmp_path: Path) -> None:
    p = tmp_path / "test.json"
    atomic_write_json(p, {"a": 1}, indent=None)
    text = p.read_text(encoding="utf-8")
    assert "\n" not in text


def test_atomic_write_json_non_ascii(tmp_path: Path) -> None:
    p = tmp_path / "test.json"
    atomic_write_json(p, {"msg": "日本語"})
    text = p.read_text(encoding="utf-8")
    assert "日本語" in text
    assert "\\u" not in text


def test_atomic_write_json_default_serializer(tmp_path: Path) -> None:
    from datetime import date

    p = tmp_path / "test.json"
    atomic_write_json(p, {"d": date(2026, 1, 1)})
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["d"] == "2026-01-01"
