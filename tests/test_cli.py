"""CLI コマンドのスモークテスト（typer の CliRunner 経由）。"""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_schema_list(runner):
    result = runner.invoke(app, ["schema", "list"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert "power" in data
    names = {c["name"] for c in data["power"]}
    assert "battery" in names


def test_schema_show(runner):
    result = runner.invoke(app, ["schema", "show", "power", "battery"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert "properties" in body


def test_schema_show_404(runner):
    result = runner.invoke(app, ["schema", "show", "power", "unknown"])
    assert result.exit_code == 1


def test_get_instance(runner, power_data_backup):
    result = runner.invoke(app, ["get", "power", "battery", "main"])
    assert result.exit_code == 0, result.stdout
    # 出力先頭は "# ETag:" コメント
    assert "# ETag:" in result.stdout
    body = json.loads(result.stdout.split("\n", 1)[1])
    assert body["spec"]["capacity_wh"] == 100.0


def test_get_list_instances(runner, power_data_backup):
    result = runner.invoke(app, ["get", "power", "battery"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert set(body) == {"main", "aux"}


def test_merge(runner, clean_generated_dir):
    result = runner.invoke(app, ["merge"])
    assert result.exit_code == 0
    assert "Wrote" in result.stdout


def test_merge_check_after_merge(runner, clean_generated_dir):
    runner.invoke(app, ["merge"])
    result = runner.invoke(app, ["merge", "--check"])
    assert result.exit_code == 0
    assert "OK" in result.stdout


def test_scaffold_dry_run(runner, power_data_backup):
    result = runner.invoke(app, ["scaffold", "power", "--dry-run"])
    assert result.exit_code == 0
    assert "power:" in result.stdout


def test_verify_no_fail_flag(runner, clean_generated_dir):
    # 現状の data.toml では verify=False が含まれる → --no-fail-on-verify で exit 0
    result = runner.invoke(app, ["verify", "--no-fail-on-verify"])
    assert result.exit_code == 0
    assert "VERI" in result.stdout


def test_verify_default_exit_0_when_all_pass(runner, clean_generated_dir):
    """shared_spec=True で全 battery が capacity=100 → verify pass → exit 0。"""
    result = runner.invoke(app, ["verify"])
    assert result.exit_code == 0


def test_analysis_list(runner):
    result = runner.invoke(app, ["analysis", "list"])
    assert result.exit_code == 0
    items = json.loads(result.stdout)
    names = {a["name"] for a in items}
    assert "battery_eol_capacity" in names


def test_analysis_run_adhoc(runner):
    result = runner.invoke(
        app,
        [
            "analysis",
            "run",
            "_",
            "battery_eol_capacity",
            "--payload",
            json.dumps({"initial_capacity_wh": 100.0, "years": 5.0}),
        ],
    )
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["value"] == pytest.approx(81.75)


def test_analysis_run_veriq(runner, clean_generated_dir):
    result = runner.invoke(app, ["analysis", "run", "power", "total_pdm_power_w"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["value"] == 8.0


def test_init_subsystem(runner):
    """init で 4 ファイル生成。"""
    import os

    with tempfile.TemporaryDirectory() as tmp:
        # macOS では /var → /private/var の symlink があるので resolve
        tmp_path = Path(tmp).resolve()
        (tmp_path / "subsystems").mkdir()
        prev_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["init", "subsystem", "demo", "--kind", "hardware"])
        finally:
            os.chdir(prev_cwd)
        created_dir = tmp_path / "subsystems" / "demo"
        assert result.exit_code == 0, result.stdout
        assert (created_dir / "components.py").exists()
        assert (created_dir / "scope.py").exists()
        assert (created_dir / "data.toml").exists()
        assert (created_dir / "__init__.py").exists()


def test_init_subsystem_already_exists(runner):
    """既存ディレクトリへ init は失敗する。"""
    result = runner.invoke(app, ["init", "subsystem", "power"])
    assert result.exit_code == 1
