"""schema.codegen — Pydantic model building and .pyi stub generation."""

from schema.codegen.root_model_builder import build_system_root_model
from schema.codegen.stubgen import (
    STUB_FILENAME,
    apply_ruff_format,
    render_subsystem_stub,
)

__all__ = [
    "STUB_FILENAME",
    "apply_ruff_format",
    "build_system_root_model",
    "render_subsystem_stub",
]
