"""git history / diff API and CLI tests."""

import re

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from craft.api.main import app as api_app
from craft.cli.main import app as cli_app
from craft.core.persistence.history import GitRefNotFound, git_diff, git_log


def test_git_log_returns_entries():
    entries = git_log(limit=3)
    assert len(entries) <= 3
    for entry in entries:
        assert re.fullmatch(r"[0-9a-f]{40}", entry.sha)
        assert entry.author
        assert entry.date
        assert entry.message


def test_git_log_path_filter():
    assert git_log("does/not/exist.toml") == []


def test_git_diff_unknown_sha_raises():
    try:
        git_diff("nonexistent", "HEAD")
    except GitRefNotFound:
        return
    raise AssertionError("git_diff should raise GitRefNotFound for an unknown ref")


def test_git_diff_head_head_empty():
    assert git_diff("HEAD", "HEAD").strip() == ""


def test_api_history_endpoint():
    with TestClient(api_app) as client:
        response = client.get("/history", params={"limit": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["path"] is None
    assert len(body["entries"]) <= 3


def test_api_diff_404_on_bad_sha():
    with TestClient(api_app) as client:
        response = client.get("/diff", params={"from": "nonexistent", "to": "HEAD"})
    assert response.status_code == 404


def test_cli_history():
    result = CliRunner().invoke(cli_app, ["history", "--limit", "3"])
    assert result.exit_code == 0, result.stdout
