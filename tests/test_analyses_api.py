"""@analysis 自動 API 化のテスト。"""

from fastapi.testclient import TestClient

from api.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_list_analyses_includes_all_kinds():
    with _client() as c:
        r = c.get("/analyses")
    assert r.status_code == 200
    names = {a["name"] for a in r.json()["analyses"]}
    assert {"total_pdm_power_w", "verify_battery_capacity", "battery_eol_capacity"} <= names


def test_get_analysis_ref_inputs():
    with _client() as c:
        r = c.get("/analyses/power/total_pdm_power_w")
    assert r.status_code == 200
    body = r.json()
    assert body["adhoc"] is False
    assert any(ref["name"] == "pdms" for ref in body["ref_inputs"])
    assert body["return_annotation"] == "float"


def test_get_analysis_adhoc_inputs():
    with _client() as c:
        r = c.get("/analyses/_/battery_eol_capacity")
    assert r.status_code == 200
    body = r.json()
    assert body["adhoc"] is True
    assert {p["name"] for p in body["direct_inputs"]} == {
        "initial_capacity_wh",
        "years",
        "cycles_per_day",
    }


def test_get_analysis_404():
    with _client() as c:
        r = c.get("/analyses/power/nonexistent")
    assert r.status_code == 404
    assert r.json()["type"] == "not_found"


def test_run_adhoc_analysis():
    with _client() as c:
        r = c.post(
            "/analyses/_/battery_eol_capacity",
            json={"initial_capacity_wh": 100.0, "years": 5.0, "cycles_per_day": 2.0},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["analysis"] == "battery_eol_capacity"
    # 5 * 365 * 2 = 3650 cycles → 0.0001 * 3650 = 0.365 → cap at 0.2 → 100 * 0.8 = 80
    assert body["value"] == 80.0


def test_run_adhoc_uses_defaults():
    """payload を省くと default が使われる。"""
    with _client() as c:
        r = c.post(
            "/analyses/_/battery_eol_capacity",
            json={"initial_capacity_wh": 200.0},
        )
    assert r.status_code == 200
    # 5 * 365 * 1 = 1825 → 0.1825 → 200 * (1 - 0.1825) = 163.5
    assert abs(r.json()["value"] - 163.5) < 0.01


def test_run_veriq_calculation(clean_generated_dir):
    with _client() as c:
        r = c.post("/analyses/power/total_pdm_power_w")
    assert r.status_code == 200
    body = r.json()
    assert body["value"] == 8.0
    assert body["verify"] is False


def test_run_veriq_verification(clean_generated_dir):
    with _client() as c:
        r = c.post("/analyses/power/verify_battery_capacity")
    assert r.status_code == 200
    body = r.json()
    assert body["verify"] is True
    # shared_spec=True: 全 battery が capacity=100 → 80 >= 50 → True
    assert body["value"] is True
