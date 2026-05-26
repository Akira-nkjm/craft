"""Architecture guard + ETag mismatch tests for CLI and MCP.

Acceptance criteria:
- core/ has no `from api.*` imports (architecture guard)
- CLI: ETag mismatch → exit 1 + formatted message
- MCP: ETag mismatch → {"error": ...} response
"""

import ast
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from core.errors import ETagMismatch, PreconditionRequired
from mcp_server.handlers import (
    handle_delete_instance,
    handle_patch_instance,
)

# ─── architecture guard ─────────────────────────────────────────────


def test_no_api_import_in_core():
    """core/ must not import from api.*"""
    core_dir = Path(__file__).parent.parent / "core"
    violations: list[str] = []
    for py_file in sorted(core_dir.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("api"):
                violations.append(
                    f"{py_file.relative_to(core_dir.parent)}: from {node.module} import ..."
                )
    assert violations == [], "core/ contains api.* imports:\n" + "\n".join(violations)


# ─── CLI ETag mismatch ───────────────────────────────────────────────


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_put_etag_mismatch(runner, power_data_backup):
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.65},
            "requirements": {"depth_of_discharge_max": 0.8},
        }
    )
    result = runner.invoke(
        app,
        ["put", "power", "battery", "main", "--etag", 'W/"sha256:wrong"', "--json", payload],
    )
    assert result.exit_code == 1
    assert "Error:" in result.output or "Error:" in (result.stderr or "")


def test_cli_patch_etag_mismatch(runner, power_data_backup):
    delta = json.dumps({"design": {"depth_of_discharge": 0.5}})
    result = runner.invoke(
        app,
        ["patch", "power", "battery", "main", "--etag", 'W/"sha256:wrong"', "--json", delta],
    )
    assert result.exit_code == 1
    assert "Error:" in result.output or "Error:" in (result.stderr or "")


def test_cli_delete_etag_mismatch(runner, power_data_backup):
    result = runner.invoke(
        app,
        ["delete", "power", "battery", "main", "--etag", 'W/"sha256:wrong"'],
    )
    assert result.exit_code == 1
    assert "Error:" in result.output or "Error:" in (result.stderr or "")


def test_cli_put_correct_etag_succeeds(runner, power_data_backup):
    """Happy path: auto-resolved ETag (no --etag flag) succeeds."""
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.65},
            "requirements": {"depth_of_discharge_max": 0.8},
        }
    )
    result = runner.invoke(app, ["put", "power", "battery", "main", "--json", payload])
    assert result.exit_code == 0, result.output
    assert "# ETag:" in result.output


# ─── MCP ETag mismatch ───────────────────────────────────────────────


def test_mcp_patch_instance_etag_mismatch(power_data_backup):
    """handle_patch_instance with wrong etag returns {"error": ...}."""
    result = handle_patch_instance(
        "power",
        "battery",
        {
            "name": "main",
            "delta": {"design": {"depth_of_discharge": 0.5}},
            "etag": 'W/"sha256:wrong"',
        },
    )
    assert "error" in result
    assert isinstance(result["error"], str)
    assert len(result["error"]) > 0


def test_mcp_delete_instance_etag_mismatch(power_data_backup):
    """handle_delete_instance with wrong etag returns {"error": ...}."""
    result = handle_delete_instance(
        "power",
        "battery",
        {"name": "main", "etag": 'W/"sha256:wrong"'},
    )
    assert "error" in result
    assert isinstance(result["error"], str)


def test_mcp_patch_instance_happy_path(power_data_backup):
    """handle_patch_instance with no explicit etag (auto-resolve) succeeds."""
    result = handle_patch_instance(
        "power",
        "battery",
        {
            "name": "main",
            "delta": {"design": {"depth_of_discharge": 0.5}},
        },
    )
    assert "error" not in result, result
    assert "etag" in result


def test_mcp_delete_instance_happy_path(power_data_backup):
    """handle_delete_instance with no explicit etag (auto-resolve) succeeds."""
    result = handle_delete_instance(
        "power",
        "battery",
        {"name": "aux"},
    )
    assert "error" not in result, result
    assert result.get("deleted") is True


# ─── core.errors direct unit tests ──────────────────────────────────


def test_precondition_required_is_craft_error():
    from core.errors import CraftError

    exc = PreconditionRequired("test")
    assert isinstance(exc, CraftError)
    assert str(exc) == "test"


def test_etag_mismatch_is_craft_error():
    from core.errors import CraftError

    exc = ETagMismatch("mismatch")
    assert isinstance(exc, CraftError)
    assert str(exc) == "mismatch"
