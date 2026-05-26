"""Cross-surface consistency tests for core/operations.py.

Verifies that InstanceNotFound, SharedSpecConflict, SingletonNotInstanceable,
ETagMismatch, and PreconditionRequired each produce equivalent error outcomes
on all three surfaces (API, CLI, MCP).
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from api.main import app as fastapi_app
from cli.main import app as cli_app
from core.errors import ETagMismatch, PreconditionRequired
from core.instances import (
    InstanceNotFound,
    SharedSpecConflict,
    SingletonNotInstanceable,
)
from mcp_server.handlers import handle_add_instance, handle_delete_instance, handle_patch_instance

# ── helpers ─────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    with TestClient(fastapi_app) as client:
        yield client


@pytest.fixture
def runner():
    return CliRunner()


def _patch_create(exc: Exception):
    return patch("core.operations.create_instance", side_effect=exc)


def _patch_delete(exc: Exception):
    return patch("core.operations.delete_instance", side_effect=exc)


def _patch_patch(exc: Exception):
    return patch("core.operations.patch_instance", side_effect=exc)


# ── SharedSpecConflict: create ───────────────────────────────────────


class TestSharedSpecConflictOnCreate:
    """SharedSpecConflict during create → conflict on every surface."""

    exc = SharedSpecConflict("payload.spec differs from shared spec")

    def test_api_returns_409(self, api_client):
        with _patch_create(self.exc):
            r = api_client.post(
                "/components/power/battery/new",
                json={"design": {"depth_of_discharge": 0.5}},
            )
        assert r.status_code == 409

    def test_cli_exits_1(self, runner):
        with _patch_create(self.exc):
            result = runner.invoke(
                cli_app,
                ["create", "power", "battery", "new", "--json", '{"design": {}}'],
            )
        assert result.exit_code == 1
        assert "Error:" in result.output or "Error:" in (result.stderr or "")

    def test_mcp_returns_error_dict(self):
        with _patch_create(self.exc):
            out = handle_add_instance("power", "battery", {"name": "new", "design": {}})
        assert "error" in out


# ── SingletonNotInstanceable: create ────────────────────────────────


class TestSingletonNotInstanceableOnCreate:
    """SingletonNotInstanceable during create → conflict on every surface."""

    exc = SingletonNotInstanceable("Singleton does not support instance creation")

    def test_api_returns_409(self, api_client):
        with _patch_create(self.exc):
            r = api_client.post(
                "/components/power/battery/new",
                json={"design": {}},
            )
        assert r.status_code == 409

    def test_cli_exits_1(self, runner):
        with _patch_create(self.exc):
            result = runner.invoke(
                cli_app,
                ["create", "power", "battery", "new", "--json", '{"design": {}}'],
            )
        assert result.exit_code == 1

    def test_mcp_returns_error_dict(self):
        with _patch_create(self.exc):
            out = handle_add_instance("power", "battery", {"name": "new", "design": {}})
        assert "error" in out


# ── InstanceNotFound: delete ─────────────────────────────────────────


class TestInstanceNotFoundOnDelete:
    """InstanceNotFound during delete → not_found on every surface."""

    exc = InstanceNotFound("Instance 'power.battery.ghost' not found")

    def test_api_returns_404(self, api_client):
        with _patch_delete(self.exc):
            r = api_client.delete(
                "/components/power/battery/ghost",
                headers={"If-Match": 'W/"sha256:abc"'},
            )
        assert r.status_code == 404

    def test_cli_exits_1(self, runner):
        with _patch_delete(self.exc):
            result = runner.invoke(
                cli_app,
                ["delete", "power", "battery", "ghost", "--etag", 'W/"sha256:abc"'],
            )
        assert result.exit_code == 1

    def test_mcp_returns_error_dict(self):
        with _patch_delete(self.exc):
            out = handle_delete_instance(
                "power", "battery", {"name": "ghost", "etag": 'W/"sha256:abc"'}
            )
        assert "error" in out


# ── SharedSpecConflict: delete (previously uncaught on API & MCP) ────


class TestSharedSpecConflictOnDelete:
    """SharedSpecConflict during delete → conflict on every surface.

    This is the specific bug from issue #12: API and MCP did not catch
    SharedSpecConflict in DELETE handlers, causing 500 / unhandled error.
    """

    exc = SharedSpecConflict("spec conflict on delete")

    def test_api_returns_409_not_500(self, api_client):
        with _patch_delete(self.exc):
            r = api_client.delete(
                "/components/power/battery/main",
                headers={"If-Match": 'W/"sha256:abc"'},
            )
        assert r.status_code == 409

    def test_cli_exits_1(self, runner):
        with _patch_delete(self.exc):
            result = runner.invoke(
                cli_app,
                ["delete", "power", "battery", "main", "--etag", 'W/"sha256:abc"'],
            )
        assert result.exit_code == 1

    def test_mcp_returns_error_dict(self):
        with _patch_delete(self.exc):
            out = handle_delete_instance(
                "power", "battery", {"name": "main", "etag": 'W/"sha256:abc"'}
            )
        assert "error" in out


# ── ETagMismatch: patch ───────────────────────────────────────────────


class TestETagMismatchOnPatch:
    """ETagMismatch during patch → etag_mismatch on every surface."""

    exc = ETagMismatch("If-Match did not match current ETag")

    def test_api_returns_412(self, api_client):
        with _patch_patch(self.exc):
            r = api_client.patch(
                "/components/power/battery/main",
                json={"design": {}},
                headers={"If-Match": 'W/"sha256:stale"'},
            )
        assert r.status_code == 412

    def test_cli_exits_1(self, runner):
        with _patch_patch(self.exc):
            result = runner.invoke(
                cli_app,
                [
                    "patch",
                    "power",
                    "battery",
                    "main",
                    "--json",
                    '{"design": {}}',
                    "--etag",
                    'W/"sha256:stale"',
                ],
            )
        assert result.exit_code == 1

    def test_mcp_returns_error_dict(self):
        with _patch_patch(self.exc):
            out = handle_patch_instance(
                "power",
                "battery",
                {"name": "main", "delta": {}, "etag": 'W/"sha256:stale"'},
            )
        assert "error" in out


# ── PreconditionRequired: patch ───────────────────────────────────────


class TestPreconditionRequiredOnPatch:
    """PreconditionRequired during patch → precondition on every surface."""

    exc = PreconditionRequired("If-Match header is required")

    def test_api_returns_428(self, api_client):
        with _patch_patch(self.exc):
            r = api_client.patch(
                "/components/power/battery/main",
                json={"design": {}},
            )
        assert r.status_code == 428

    def test_cli_exits_1(self, runner):
        with _patch_patch(self.exc):
            result = runner.invoke(
                cli_app,
                [
                    "patch",
                    "power",
                    "battery",
                    "main",
                    "--json",
                    '{"design": {}}',
                    "--etag",
                    'W/"sha256:x"',
                ],
            )
        assert result.exit_code == 1

    def test_mcp_returns_error_dict(self):
        with _patch_patch(self.exc):
            out = handle_patch_instance(
                "power",
                "battery",
                {"name": "main", "delta": {}, "etag": 'W/"sha256:x"'},
            )
        assert "error" in out
