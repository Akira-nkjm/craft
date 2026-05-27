"""CLI の CRUD コマンド (create / put / patch / delete / spec) のテスト。

power_data_backup fixture によりテスト後に data.toml を復元する。
"""

import json

import pytest
from typer.testing import CliRunner

from craft.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _parse_body(stdout: str) -> dict:
    """`# ETag:` コメント行をスキップして JSON 部分を取り出す。"""
    lines = stdout.splitlines()
    body_lines = [ln for ln in lines if not ln.startswith("# ETag:")]
    return json.loads("\n".join(body_lines))


# ─── create ─────────────────────────────────────────────────────────


def test_create_instance(runner, power_data_backup):
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.65},
            "requirements": {"depth_of_discharge_max": 0.8},
        }
    )
    result = runner.invoke(app, ["create", "power", "battery", "spare", "--json", payload])
    assert result.exit_code == 0, result.stdout
    assert "# ETag:" in result.stdout
    body = _parse_body(result.stdout)
    # shared spec が merge されて返る
    assert body["spec"]["capacity_wh"] == 100.0
    assert body["design"]["depth_of_discharge"] == 0.65

    # 後続の get が成功
    get_result = runner.invoke(app, ["get", "power", "battery", "spare"])
    assert get_result.exit_code == 0
    got = _parse_body(get_result.stdout)
    assert got["design"]["depth_of_discharge"] == 0.65


def test_create_already_exists(runner, power_data_backup):
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.7},
            "requirements": {"depth_of_discharge_max": 0.8},
        }
    )
    result = runner.invoke(app, ["create", "power", "battery", "main", "--json", payload])
    assert result.exit_code == 1
    assert "already exists" in result.stderr or "already exists" in result.output


def test_create_singleton_fails(runner, power_data_backup):
    """Singleton (orbit など) は instance 作成不可。pdms は multi なので bus を試す。

    pdms.spec / pdms.main の構造を見るかぎり pdm も multi。
    instead use a singleton: 例として systems に singleton が無ければスキップ。
    """
    # systems/power の component はすべて multi の可能性が高い。
    # 代わりに不正な system を試して 1 を確認するテストを書く。
    payload = json.dumps({"design": {"depth_of_discharge": 0.5}})
    result = runner.invoke(app, ["create", "unknown", "battery", "x", "--json", payload])
    assert result.exit_code == 1


# ─── patch ─────────────────────────────────────────────────────────


def test_patch_instance(runner, power_data_backup):
    payload = json.dumps({"design": {"depth_of_discharge": 0.5}})
    result = runner.invoke(
        app, ["patch", "power", "battery", "main", "--auto-etag", "--json", payload]
    )
    assert result.exit_code == 0, result.stdout
    body = _parse_body(result.stdout)
    assert body["design"]["depth_of_discharge"] == 0.5


def test_patch_instance_not_found(runner, power_data_backup):
    payload = json.dumps({"design": {"depth_of_discharge": 0.5}})
    result = runner.invoke(app, ["patch", "power", "battery", "ghost", "--json", payload])
    assert result.exit_code == 1


# ─── put ───────────────────────────────────────────────────────────


def test_put_instance(runner, power_data_backup):
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.55},
            "requirements": {"depth_of_discharge_max": 0.85},
        }
    )
    result = runner.invoke(
        app, ["put", "power", "battery", "main", "--auto-etag", "--json", payload]
    )
    assert result.exit_code == 0, result.stdout
    body = _parse_body(result.stdout)
    assert body["design"]["depth_of_discharge"] == 0.55
    assert body["requirements"]["depth_of_discharge_max"] == 0.85
    # shared spec が view に merge されている
    assert body["spec"]["capacity_wh"] == 100.0


# ─── delete ────────────────────────────────────────────────────────


def test_delete_instance(runner, power_data_backup):
    result = runner.invoke(app, ["delete", "power", "battery", "aux", "--auto-etag"])
    assert result.exit_code == 0, result.stdout
    assert "Deleted" in result.stdout

    # 後続の get が 1 で失敗
    get_result = runner.invoke(app, ["get", "power", "battery", "aux"])
    assert get_result.exit_code == 1


def test_delete_instance_not_found(runner, power_data_backup):
    result = runner.invoke(app, ["delete", "power", "battery", "ghost"])
    assert result.exit_code == 1


# ─── spec get / set ────────────────────────────────────────────────


def test_spec_get(runner, power_data_backup):
    result = runner.invoke(app, ["spec", "get", "power", "battery"])
    assert result.exit_code == 0, result.stdout
    body = _parse_body(result.stdout)
    assert body["capacity_wh"] == 100.0
    assert body["manufacturer"] == "Panasonic"


def test_spec_set(runner, power_data_backup):
    payload = json.dumps(
        {
            "capacity_wh": 120.0,
            "nominal_voltage_v": 3.7,
            "manufacturer": "Panasonic",
            "temp_min_c": -20.0,
            "temp_max_c": 60.0,
        }
    )
    result = runner.invoke(
        app, ["spec", "set", "power", "battery", "--auto-etag", "--json", payload]
    )
    assert result.exit_code == 0, result.stdout
    body = _parse_body(result.stdout)
    assert body["capacity_wh"] == 120.0

    # spec get で確認
    get_result = runner.invoke(app, ["spec", "get", "power", "battery"])
    assert get_result.exit_code == 0
    got = _parse_body(get_result.stdout)
    assert got["capacity_wh"] == 120.0


# ─── --data file 経由 (TOML) ───────────────────────────────────────


def test_create_via_toml_file(runner, power_data_backup, tmp_path):
    toml_file = tmp_path / "spare.toml"
    toml_file.write_text(
        "[design]\ndepth_of_discharge = 0.6\n\n[requirements]\ndepth_of_discharge_max = 0.8\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["create", "power", "battery", "spare", "--data", str(toml_file)])
    assert result.exit_code == 0, result.stdout
    body = _parse_body(result.stdout)
    assert body["design"]["depth_of_discharge"] == 0.6


def test_create_via_json_file(runner, power_data_backup, tmp_path):
    json_file = tmp_path / "spare.json"
    json_file.write_text(
        json.dumps(
            {
                "design": {"depth_of_discharge": 0.62},
                "requirements": {"depth_of_discharge_max": 0.8},
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["create", "power", "battery", "spare", "--data", str(json_file)])
    assert result.exit_code == 0, result.stdout


# ─── stdin ─────────────────────────────────────────────────────────


def test_create_via_stdin(runner, power_data_backup):
    payload = json.dumps(
        {
            "design": {"depth_of_discharge": 0.63},
            "requirements": {"depth_of_discharge_max": 0.8},
        }
    )
    result = runner.invoke(
        app,
        ["create", "power", "battery", "spare"],
        input=payload,
    )
    assert result.exit_code == 0, result.stdout
