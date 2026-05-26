# チュートリアル：新しい subsystem を追加する

ACS（姿勢制御）subsystem を例に、ゼロから subsystem を追加する手順を通して学ぶ。

!!! abstract "このチュートリアルで学ぶこと"
    - `craft init subsystem` で雛形を生成する
    - `Component` クラスと `fld()` を定義する
    - `data.toml` にインスタンスデータを書く
    - `craft merge` / `craft verify` でパイプラインを通す
    - `@analysis` で計算関数を追加する
    - テストを書く

---

## 前提

```bash
uv sync
uv run pytest -q  # 既存テストが通ることを確認
```

---

## Step 1: 雛形を生成する

```bash
uv run craft init subsystem acs
```

`subsystems/acs/` に以下が生成される：

```
subsystems/acs/
├── __init__.py
├── components.py   # Component 定義（空の例付き）
├── scope.py        # veriq Scope（ボイラープレート）
└── data.toml       # インスタンスデータ（空）
```

!!! tip "--kind オプション"
    | kind | 用途 |
    |---|---|
    | `hardware` (default) | センサ・アクチュエータ等のハードウェア |
    | `config-only` | ミッションパラメータ等の Config だけを持つ subsystem |
    | `default` | 最小限の空スケルトン |

---

## Step 2: Component を定義する

`subsystems/acs/components.py` を編集する：

```python
from schema import Component, MultiInstance, SpecOnly, fld


class ReactionWheel(Component, MultiInstance):  # (1)
    """リアクションホイール。姿勢制御トルクを発生させる。"""

    max_torque_nm: float = fld(ge=0, unit="N·m", desc="最大トルク")
    max_speed_rpm: float = fld(ge=0, unit="rpm", desc="最大回転数")
    moment_of_inertia_kgm2: float = fld(ge=0, unit="kg·m²")

    class Design:
        nominal_speed_rpm: float = fld(ge=0, default=0.0, desc="定常回転数")


class StarTracker(Component, SpecOnly):  # (2)
    """スタートラッカー。姿勢決定センサ（Design なし）。"""

    accuracy_arcsec: float = fld(ge=0, unit="arcsec", desc="指向精度")
    fov_deg: float = fld(ge=0, unit="deg", desc="視野角")
```

1. `MultiInstance` で複数インスタンスを許可（RW は通常 3〜4 個）
2. `SpecOnly` は Design を持たない datasheet 型

登録を確認する：

```bash
uv run craft schema list
```

```json
{
  "acs": [
    {"name": "reaction_wheel", "plural": "reaction_wheels", "cardinality": "multi", "traits": []},
    {"name": "star_tracker",   "plural": "star_trackers",   "cardinality": "multi", "traits": ["SpecOnly"]}
  ]
}
```

---

## Step 3: data.toml にインスタンスを書く

`subsystems/acs/data.toml` を編集する。先に `scaffold` で雛形を生成するのが便利：

```bash
uv run craft scaffold acs --dry-run  # 差分を確認
uv run craft scaffold acs            # data.toml に追記
```

値を埋める：

```toml
# ACS subsystem instance data

# === Reaction Wheels (MultiInstance: shared spec) ===

[reaction_wheels.spec]
max_torque_nm = 0.2
max_speed_rpm = 6000.0
moment_of_inertia_kgm2 = 0.00035

[reaction_wheels.x.design]
nominal_speed_rpm = 0.0

[reaction_wheels.y.design]
nominal_speed_rpm = 0.0

[reaction_wheels.z.design]
nominal_speed_rpm = 0.0


# === Star Tracker (SpecOnly: no Design) ===

[star_trackers.spec]
accuracy_arcsec = 5.0
fov_deg = 20.0
```

!!! note "Singleton vs MultiInstance の data.toml"
    - **Singleton** (`single`): `[<plural>.spec]` / `[<plural>.design]` と直接書く
    - **MultiInstance** (`multi`): `[<plural>.spec]` に共通 spec、`[<plural>.<name>.design]` にインスタンス固有データ

---

## Step 4: merge して確認する

```bash
uv run craft merge --check   # エラーがないか確認（generated/ は変更しない）
uv run craft merge           # generated/merged.toml に反映
```

インスタンスを取得して確認：

```bash
uv run craft get acs reaction_wheel x
```

```
# ETag: abc123
{
  "spec": {
    "max_torque_nm": 0.2,
    "max_speed_rpm": 6000.0,
    "moment_of_inertia_kgm2": 0.00035
  },
  "design": {
    "nominal_speed_rpm": 0.0
  },
  "meta": null
}
```

---

## Step 5: Analysis を追加する（任意）

`subsystems/acs/analyses.py` を新規作成する：

```python
from typing import Annotated
import veriq as vq
from schema import analysis


@analysis(desc="リアクションホイールの最大トルク合計 (N·m)")
def total_rw_torque_nm(
    reaction_wheels: Annotated[vq.Table, vq.Ref("$.reaction_wheels")],
) -> float:
    return sum(rw.spec.max_torque_nm for rw in reaction_wheels.values())


@analysis(verify=True, desc="全 RW のトルクが 0.1 N·m 以上")
def rw_torque_sufficient(
    reaction_wheels: Annotated[vq.Table, vq.Ref("$.reaction_wheels")],
) -> bool:
    return all(rw.spec.max_torque_nm >= 0.1 for rw in reaction_wheels.values())
```

!!! tip "scope.py は編集不要"
    `@analysis` を追加するだけで自動的に scope に登録される。

登録確認と実行：

```bash
uv run craft analysis list
uv run craft analysis run acs rw_torque_sufficient
```

---

## Step 6: verify を通す

```bash
uv run craft verify
```

成功例：

```
  CALC power/@total_pdm_power_w  =  8.0
  VERI ✓ power/?verify_battery_capacity  =  True
  VERI ✓ acs/?rw_torque_sufficient  =  True
success=True, errors=0, run_id=20260526_120000_abc
```

!!! warning "verification が失敗した場合"
    `VERI ✗` が出た場合は `data.toml` の値か `Requirements` の設定を見直す。
    `--no-fail-on-verify` フラグで exit code を 0 にして詳細確認できる。

---

## Step 7: テストを書く

`tests/test_acs.py` を追加する：

```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_acs_schema_list():
    resp = client.get("/schema/acs")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "reaction_wheel" in names
    assert "star_tracker" in names


def test_get_reaction_wheel_instance():
    resp = client.get("/components/acs/reaction_wheel/x")
    assert resp.status_code == 200
    data = resp.json()
    assert data["spec"]["max_torque_nm"] == pytest.approx(0.2)


def test_rw_torque_analysis():
    resp = client.post("/analyses/acs/rw_torque_sufficient/run")
    assert resp.status_code == 200
    assert resp.json()["value"] is True
```

```bash
uv run pytest tests/test_acs.py -v
```

---

## まとめ

| ファイル | 変更内容 |
|---|---|
| `subsystems/acs/components.py` | Component クラスを定義 |
| `subsystems/acs/data.toml` | インスタンスデータを記述 |
| `subsystems/acs/analyses.py` | Analysis 関数を追加（任意） |
| `subsystems/acs/scope.py` | 新 subsystem 追加時に生成（以降は編集不要） |
| `tests/test_acs.py` | テスト |

!!! success "api / cli / mcp_server は一切触らない"
    Component を定義するだけで、API エンドポイント・CLI コマンド・MCP tool が自動的に増える。
    これが Craft の核心的な設計思想。
