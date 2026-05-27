"""core.io — TOML I/O and atomic write utilities."""

from core.io.atomic_write import (
    atomic_write_bytes,
    atomic_write_bytes_or_text,
    atomic_write_json,
    atomic_write_text,
)
from core.io.toml_io import read_toml, read_toml_doc, write_toml_atomic

__all__ = [
    "atomic_write_bytes",
    "atomic_write_bytes_or_text",
    "atomic_write_json",
    "atomic_write_text",
    "read_toml",
    "read_toml_doc",
    "write_toml_atomic",
]
