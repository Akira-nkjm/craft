"""components CRUD + ETag + If-Match + RFC 7807 のテスト。"""

from fastapi.testclient import TestClient

from api.main import app


def _client() -> TestClient:
    return TestClient(app)


# ─── GET ─────────────────────────────────────────────────────────────


def test_get_instance_returns_etag(power_data_backup):
    with _client() as c:
        r = c.get("/components/power/battery/main")
    assert r.status_code == 200
    assert r.headers["etag"].startswith('W/"sha256:')
    assert r.json()["spec"]["capacity_wh"] == 100.0


def test_get_instance_404(power_data_backup):
    with _client() as c:
        r = c.get("/components/power/battery/missing")
    assert r.status_code == 404
    body = r.json()
    assert body["type"] == "not_found"
    assert body["status"] == 404
    assert body["instance"] == "/components/power/battery/missing"


# ─── POST (create) ───────────────────────────────────────────────────


def test_post_creates_new_instance(power_data_backup):
    # shared_spec=True: payload は design / requirements のみ。spec を省略すれば
    # GET 時に shared spec が merge されて返る。
    payload = {
        "design": {"depth_of_discharge": 0.7},
        "requirements": {"depth_of_discharge_max": 0.8},
    }
    with _client() as c:
        r = c.post("/components/power/battery/spare", json=payload)
    assert r.status_code == 201
    assert r.headers["etag"]
    # view には shared spec が merge される
    assert r.json()["spec"]["capacity_wh"] == 100.0


def test_post_conflict_when_exists(power_data_backup):
    payload = {
        "spec": {
            "capacity_wh": 75.0,
            "nominal_voltage_v": 3.7,
            "manufacturer": "Saft",
            "operating_temperature_min_c": -20.0,
            "operating_temperature_max_c": 60.0,
        },
        "design": {"depth_of_discharge": 0.7},
        "requirements": {"depth_of_discharge_max": 0.8},
    }
    with _client() as c:
        r = c.post("/components/power/battery/main", json=payload)
    assert r.status_code == 409
    assert r.json()["type"] == "conflict"


def test_post_validation_error_returns_rfc7807(power_data_backup):
    """完全な payload で capacity_wh が ge=0 違反 → 422 + RFC 7807。"""
    payload = {
        "spec": {
            "capacity_wh": -10.0,  # ge=0 違反
            "nominal_voltage_v": 3.7,
            "manufacturer": "Bad",
            "operating_temperature_min_c": -20.0,
            "operating_temperature_max_c": 60.0,
        },
        "design": {"depth_of_discharge": 0.7},
        "requirements": {"depth_of_discharge_max": 0.8},
    }
    with _client() as c:
        r = c.post("/components/power/battery/badcap", json=payload)
    assert r.status_code == 422
    body = r.json()
    assert body["type"] == "validation_error"
    # ネストしたパス含めて capacity_wh への参照があるはず
    all_locs = [str(e["loc"]) for e in body["errors"]]
    assert any("capacity_wh" in loc for loc in all_locs), body


# ─── PUT / PATCH (require If-Match) ──────────────────────────────────


def test_put_requires_if_match(power_data_backup):
    payload = {
        "spec": {
            "capacity_wh": 200.0,
            "nominal_voltage_v": 3.7,
            "manufacturer": "Saft",
            "operating_temperature_min_c": -20.0,
            "operating_temperature_max_c": 60.0,
        },
        "design": {"depth_of_discharge": 0.7},
        "requirements": {"depth_of_discharge_max": 0.8},
    }
    with _client() as c:
        r = c.put("/components/power/battery/main", json=payload)
    assert r.status_code == 428
    assert r.json()["type"] == "if_match_required"


def test_put_etag_mismatch(power_data_backup):
    payload = {
        "spec": {
            "capacity_wh": 200.0,
            "nominal_voltage_v": 3.7,
            "manufacturer": "Saft",
            "operating_temperature_min_c": -20.0,
            "operating_temperature_max_c": 60.0,
        },
        "design": {"depth_of_discharge": 0.7},
        "requirements": {"depth_of_discharge_max": 0.8},
    }
    with _client() as c:
        r = c.put(
            "/components/power/battery/main",
            json=payload,
            headers={"If-Match": 'W/"sha256:deadbeef"'},
        )
    assert r.status_code == 412
    assert r.json()["type"] == "etag_mismatch"


def test_put_with_correct_etag_replaces(power_data_backup):
    """shared_spec=True: PUT は design / requirements の更新が中心。
    spec は省略すれば既存 shared がそのまま使われる。"""
    with _client() as c:
        got = c.get("/components/power/battery/main")
        etag = got.headers["etag"]

        payload = {
            "design": {"depth_of_discharge": 0.5},
            "requirements": {"depth_of_discharge_max": 0.9},
        }
        r = c.put(
            "/components/power/battery/main",
            json=payload,
            headers={"If-Match": etag},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["design"]["depth_of_discharge"] == 0.5
    # shared spec は変わらず view に含まれる
    assert body["spec"]["capacity_wh"] == 100.0
    assert r.headers["etag"] != etag


def test_patch_merges_partial(power_data_backup):
    """PATCH は design など instance 固有 field のみ。spec 変更は別 endpoint。"""
    with _client() as c:
        got = c.get("/components/power/battery/main")
        etag = got.headers["etag"]
        r = c.patch(
            "/components/power/battery/main",
            json={"design": {"depth_of_discharge": 0.5}},
            headers={"If-Match": etag},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["design"]["depth_of_discharge"] == 0.5
    # 他 field は保持（shared spec が view に merge される）
    assert body["spec"]["capacity_wh"] == 100.0


def test_patch_shared_spec_conflict(power_data_backup):
    """instance への spec 変更要求は 409。"""
    with _client() as c:
        got = c.get("/components/power/battery/main")
        etag = got.headers["etag"]
        r = c.patch(
            "/components/power/battery/main",
            json={"spec": {"manufacturer": "Other"}},
            headers={"If-Match": etag},
        )
    assert r.status_code == 409


# ─── DELETE ──────────────────────────────────────────────────────────


def test_delete_requires_if_match(power_data_backup):
    with _client() as c:
        r = c.delete("/components/power/battery/aux")
    assert r.status_code == 428


def test_delete_succeeds(power_data_backup):
    with _client() as c:
        got = c.get("/components/power/battery/aux")
        etag = got.headers["etag"]
        r = c.delete(
            "/components/power/battery/aux",
            headers={"If-Match": etag},
        )
        assert r.status_code == 204
        after = c.get("/components/power/battery/aux")
        assert after.status_code == 404
