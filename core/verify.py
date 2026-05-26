"""Shared verification execution logic."""

import hashlib
import importlib
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import veriq as vq

from core.runs import (
    create_run_dir,
    new_run_id,
    update_latest,
    write_run_artifacts,
)
from core.serialization import to_jsonable
from core.veriq_project import build_project

merge_mod = importlib.import_module("core.merge")


def run_verify_core() -> dict[str, Any]:
    project = build_project()
    started = time.monotonic()

    merge_result, _ = merge_mod.merge()
    input_bytes = merge_mod.MERGED_TOML.read_bytes()
    input_sha = hashlib.sha256(input_bytes).hexdigest()

    model_data = vq.load_model_data_from_toml(project, merge_mod.MERGED_TOML)
    result = vq.evaluate_project(project, model_data)

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
    payload.update(
        {
            "run_id": run_id,
            "merge": {
                "systems": list(merge_result.systems),
                "source_files": merge_result.source_files,
            },
        }
    )
    return payload


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
