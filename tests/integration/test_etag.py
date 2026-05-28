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

from craft.cli.main import app
from craft.core.errors import ETagMismatch, PreconditionRequired
from craft.mcp_server.handlers import (
    handle_delete_instance,
    handle_patch_instance,
    handle_set_config,
    handle_set_config_instance,
)

# ─── architecture guard ─────────────────────────────────────────────


def test_no_api_import_in_core():
    """core/ must not import from craft.api.*"""
    core_dir = Path(__file__).resolve().parents[2] / "src" / "craft" / "core"
    violations: list[str] = []
    for py_file in sorted(core_dir.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("craft.api")
            ):
                violations.append(
                    f"{py_file.relative_to(core_dir.parent)}: from {node.module} import ..."
                )
    assert violations == [], "core/ contains craft.api.* imports:\n" + "\n".join(violations)


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
    """Happy path: --auto-etag flag fetches current ETag and write succeeds."""
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.65},
            "requirements": {"depth_of_discharge_max": 0.8},
        }
    )
    result = runner.invoke(
        app, ["put", "power", "battery", "main", "--auto-etag", "--json", payload]
    )
    assert result.exit_code == 0, result.output
    assert "# ETag:" in result.output


def test_cli_put_required_mode_no_etag_fails(runner, power_data_backup):
    """Without --etag and without --auto-etag, required mode raises error."""
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.65},
            "requirements": {"depth_of_discharge_max": 0.8},
        }
    )
    result = runner.invoke(app, ["put", "power", "battery", "main", "--json", payload])
    assert result.exit_code == 1
    assert "Error:" in result.output or "Error:" in (result.stderr or "")


def test_cli_patch_required_mode_no_etag_fails(runner, power_data_backup):
    """Without --etag and without --auto-etag, required mode raises error."""
    delta = json.dumps({"design": {"depth_of_discharge": 0.5}})
    result = runner.invoke(app, ["patch", "power", "battery", "main", "--json", delta])
    assert result.exit_code == 1
    assert "Error:" in result.output or "Error:" in (result.stderr or "")


def test_cli_delete_required_mode_no_etag_fails(runner, power_data_backup):
    """Without --etag and without --auto-etag, required mode raises error."""
    result = runner.invoke(app, ["delete", "power", "battery", "main"])
    assert result.exit_code == 1
    assert "Error:" in result.output or "Error:" in (result.stderr or "")


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
    """handle_patch_instance with auto_etag=True fetches ETag and succeeds."""
    result = handle_patch_instance(
        "power",
        "battery",
        {
            "name": "main",
            "delta": {"design": {"depth_of_discharge": 0.5}},
            "auto_etag": True,
        },
    )
    assert "error" not in result, result
    assert "etag" in result


def test_mcp_delete_instance_happy_path(power_data_backup):
    """handle_delete_instance with auto_etag=True fetches ETag and succeeds."""
    result = handle_delete_instance(
        "power",
        "battery",
        {"name": "aux", "auto_etag": True},
    )
    assert "error" not in result, result
    assert result.get("deleted") is True


def test_mcp_patch_required_mode_no_etag(power_data_backup):
    """handle_patch_instance with no etag and auto_etag=False returns error."""
    result = handle_patch_instance(
        "power",
        "battery",
        {
            "name": "main",
            "delta": {"design": {"depth_of_discharge": 0.5}},
        },
    )
    assert "error" in result
    assert isinstance(result["error"], str)
    assert len(result["error"]) > 0


def test_mcp_delete_required_mode_no_etag(power_data_backup):
    """handle_delete_instance with no etag and auto_etag=False returns error."""
    result = handle_delete_instance(
        "power",
        "battery",
        {"name": "main"},
    )
    assert "error" in result
    assert isinstance(result["error"], str)


# ─── core.errors direct unit tests ──────────────────────────────────


def test_precondition_required_is_craft_error():
    from craft.core.errors import CraftError

    exc = PreconditionRequired("test")
    assert isinstance(exc, CraftError)
    assert str(exc) == "test"


def test_etag_mismatch_is_craft_error():
    from craft.core.errors import CraftError

    exc = ETagMismatch("mismatch")
    assert isinstance(exc, CraftError)
    assert str(exc) == "mismatch"


# ─── MCP set_config (singleton) ETag — PR #37 / issue #53 ────────────
# set_config uses optional-ETag semantics: no etag = upsert without concurrency
# check; etag provided = validated against existing record if it exists.


_MISSION_PROFILE_PAYLOAD = {
    "duration_years": 3.0,
    "target_altitude_km": 550.0,
    "primary_payload": "radar",
    "contact_frequency_per_day": 3,
    "launch_window_start": "2028-01-01T00:00:00Z",
}


def test_set_config_no_etag_succeeds(mission_data_backup):
    """handle_set_config without etag succeeds (upsert, no concurrency check)."""
    result = handle_set_config("mission", "missionprofile", {"data": _MISSION_PROFILE_PAYLOAD})
    assert "error" not in result, result
    assert "etag" in result
    assert result["duration_years"] == 3.0


def test_set_config_correct_etag_succeeds(mission_data_backup):
    """handle_set_config with matching etag succeeds."""
    from craft.core.instances import get_singleton_config

    _, etag = get_singleton_config("mission", "missionprofile")
    result = handle_set_config(
        "mission", "missionprofile", {"data": _MISSION_PROFILE_PAYLOAD, "etag": etag}
    )
    assert "error" not in result, result
    assert "etag" in result


def test_set_config_wrong_etag_returns_error(mission_data_backup):
    """handle_set_config with wrong etag returns {"error": ...}."""
    result = handle_set_config(
        "mission",
        "missionprofile",
        {"data": _MISSION_PROFILE_PAYLOAD, "etag": 'W/"sha256:wrong"'},
    )
    assert "error" in result
    assert isinstance(result["error"], str)


# ─── MCP set_config_instance (multi) ETag — PR #37 / issue #53 ───────
# Bug fixed in issue #53: handler was passing the wrapper dict (including "data"
# and "etag" keys) directly to Pydantic, causing validation_error on every call.
# Now correctly extracts payload["data"] before validation.


_SAFE_MODE_PAYLOAD = {
    "description": "Test safe mode",
    "max_duration_s": 0.0,
    "is_initial_mode": True,
    "allowed_transitions": ["nominal"],
}


def test_set_config_instance_no_etag_succeeds(mission_data_backup):
    """handle_set_config_instance without etag succeeds (upsert)."""
    result = handle_set_config_instance(
        "mission", "operationmodeconfig", {"key": "safe", "data": _SAFE_MODE_PAYLOAD}
    )
    assert "error" not in result, result
    assert "etag" in result
    assert result["description"] == "Test safe mode"


def test_set_config_instance_correct_etag_succeeds(mission_data_backup):
    """handle_set_config_instance with matching etag succeeds."""
    from craft.core.instances import get_config_instance

    _, etag = get_config_instance("mission", "operationmodeconfig", "safe")
    result = handle_set_config_instance(
        "mission",
        "operationmodeconfig",
        {"key": "safe", "data": _SAFE_MODE_PAYLOAD, "etag": etag},
    )
    assert "error" not in result, result
    assert "etag" in result


def test_set_config_instance_wrong_etag_returns_error(mission_data_backup):
    """handle_set_config_instance with wrong etag returns {"error": ...}."""
    result = handle_set_config_instance(
        "mission",
        "operationmodeconfig",
        {"key": "safe", "data": _SAFE_MODE_PAYLOAD, "etag": 'W/"sha256:wrong"'},
    )
    assert "error" in result
    assert isinstance(result["error"], str)


def test_set_config_instance_missing_data_returns_error(mission_data_backup):
    """handle_set_config_instance without 'data' key returns {"error": ...}."""
    result = handle_set_config_instance("mission", "operationmodeconfig", {"key": "safe"})
    assert "error" in result
