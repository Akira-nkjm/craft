"""veriq pass-through API のテスト。"""

from urllib.parse import quote

from fastapi.testclient import TestClient

from craft.api.main import app


def test_scopes_lists_registered_scopes():
    with TestClient(app) as client:
        r = client.get("/veriq/scopes")
    assert r.status_code == 200
    body = r.json()
    names = {s["name"] for s in body["scopes"]}
    assert {"power", "cdh", "thermal", "mission"}.issubset(names)
    power = next(s for s in body["scopes"] if s["name"] == "power")
    assert "verify_battery_capacity" in power["verifications"]
    assert "total_pdm_power_w" in power["calculations"]
    assert power["verification_count"] == len(power["verifications"])


def test_nodes_returns_graph():
    with TestClient(app) as client:
        r = client.get("/veriq/nodes")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["nodes"]) == body["total"]
    for n in body["nodes"]:
        assert "path" in n
        assert "kind" in n
        assert "scope" in n


def test_nodes_filter_by_kind():
    with TestClient(app) as client:
        r = client.get("/veriq/nodes", params={"kind": "CALCULATION"})
    assert r.status_code == 200
    body = r.json()
    calc_names = {n["path"].split("@")[-1] for n in body["nodes"]}
    assert "total_pdm_power_w" in calc_names
    for n in body["nodes"]:
        assert n["kind"] == "calculation"


def test_nodes_filter_by_scope():
    with TestClient(app) as client:
        r = client.get("/veriq/nodes", params={"scope": "power"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    for n in body["nodes"]:
        assert n["scope"] == "power"


def test_nodes_unknown_kind_returns_422():
    with TestClient(app) as client:
        r = client.get("/veriq/nodes", params={"kind": "BOGUS"})
    assert r.status_code == 422


def test_node_detail():
    node_path = "power::?verify_battery_capacity"
    with TestClient(app) as client:
        r = client.get(f"/veriq/nodes/{quote(node_path, safe=':')}")
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == node_path
    assert body["kind"] == "verification"
    assert body["scope"] == "power"
    assert isinstance(body["dependencies"], list)
    assert len(body["dependencies"]) > 0


def test_node_detail_not_found():
    with TestClient(app) as client:
        r = client.get(f"/veriq/nodes/{quote('power::?missing', safe=':')}")
    assert r.status_code == 404


def test_trace():
    with TestClient(app) as client:
        r = client.get("/veriq/trace")
    assert r.status_code == 200
    body = r.json()
    assert "requirements" in body
    assert "summary" in body
    assert "total_requirements" in body["summary"]
    assert isinstance(body["requirements"], list)


def test_check_ok():
    with TestClient(app) as client:
        r = client.get("/veriq/check")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "power" in body["scopes"]


def test_schema():
    with TestClient(app) as client:
        r = client.get("/veriq/schema")
    assert r.status_code == 200
    body = r.json()
    assert "properties" in body
    props = set(body["properties"].keys())
    assert {"power", "cdh", "thermal", "mission", "orbital"}.issubset(props)
