"""Shared verification execution logic."""

import hashlib
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tomli_w
import veriq as vq

from craft.core.persistence.runs import (
    create_run_dir,
    new_run_id,
    update_latest,
    write_run_artifacts,
)
from craft.core.pipeline.veriq_project import build_project_with_scope_input
from craft.core.serialization import to_jsonable


def run_verify_core() -> dict[str, Any]:
    # SSOT: 各 scope は自分の systems/<name>/data.toml を直接読む（scope-input）。
    # merge / merged.toml には依存しない。provenance は data.toml 群のハッシュ、
    # run の input artifact は data.toml を結合した派生スナップショット。
    project = build_project_with_scope_input()
    started = time.monotonic()

    model_data = vq.load_model_data(project)
    result = vq.evaluate_project(project, model_data)

    input_bytes, input_sha, sources = _snapshot_inputs(project)

    run_id = new_run_id(input_sha=input_sha)
    create_run_dir(run_id)
    result_toml = _export_result_toml(project, model_data, result)
    duration_s = time.monotonic() - started
    meta = {
        "created_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "status": "success" if result.success else "failure",
        "duration_s": duration_s,
        "errors": [str(e) for e in result.errors],
        "input_sha": input_sha,
    }
    write_run_artifacts(
        run_id,
        result_toml=result_toml,
        input_toml=input_bytes,
        meta=meta,
    )
    update_latest(run_id)

    payload = _result_payload(result)
    payload.update({"run_id": run_id, "sources": sources})
    return payload


def _snapshot_inputs(project: vq.Project) -> tuple[bytes, str, dict[str, str]]:
    """各 scope の data.toml から provenance と結合スナップショットを作る。

    SSOT は data.toml なので、provenance は merged.toml ではなく data.toml 群の
    内容から計算する。

    Returns:
        (combined_snapshot_bytes, input_sha, {data_path: sha256}).
    """
    combined: dict[str, Any] = {}
    sources: dict[str, str] = {}
    digest = hashlib.sha256()
    for scope_name, scope in sorted(project.scopes.items()):
        src = scope.input_path
        if src is None or not src.exists():
            continue
        raw_bytes = src.read_bytes()
        combined[scope_name] = {"model": tomllib.loads(raw_bytes.decode())}
        sources[str(src)] = hashlib.sha256(raw_bytes).hexdigest()
        digest.update(str(src).encode())
        digest.update(raw_bytes)
    return tomli_w.dumps(combined).encode(), digest.hexdigest(), sources


def _export_result_toml(
    project: vq.Project,
    model_data: dict[str, Any],
    result: Any,
) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "result.toml"
        vq.export_to_toml(project, model_data, result, output)
        return output.read_bytes()


def _result_payload(result: Any) -> dict[str, Any]:
    scopes_payload: dict[str, dict[str, Any]] = {}
    for scope_name in result.scopes:
        tree = result.get_scope_tree(scope_name)
        if tree is None:
            scopes_payload[scope_name] = {"calculations": [], "verifications": []}
            continue
        scopes_payload[scope_name] = {
            "calculations": [
                {"path": str(node.path), "value": to_jsonable(node.value)}
                for node in tree.calculations
            ],
            "verifications": [
                {"path": str(node.path), "value": to_jsonable(node.value)}
                for node in tree.verifications
            ],
        }
    return {
        "success": result.success,
        "errors": [str(e) for e in result.errors],
        "scopes": scopes_payload,
    }
