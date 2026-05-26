"""Craft CLI — Typer ベース。core / schema を直接 import する offline モード。

主要コマンド:
    craft schema list                   全 component の一覧
    craft schema show <sub> <comp>      JSON Schema
    craft get <sub> <comp> [<inst>]     インスタンス取得
    craft create <sub> <comp> <inst>    インスタンス作成（--data/--json/stdin）
    craft put <sub> <comp> <inst>       インスタンス全置換（--data/--json/stdin）
    craft patch <sub> <comp> <inst>     インスタンス部分更新（--data/--json/stdin）
    craft delete <sub> <comp> <inst>    インスタンス削除
    craft spec get <sub> <comp>         MultiInstance の shared spec 取得
    craft spec set <sub> <comp>         shared spec 更新（--data/--json/stdin）
    craft merge [--check] [--dry-run]   merged.toml 再生成
    craft scaffold [<sub>] [--dry-run]  data.toml 雛形生成
    craft verify                        merge → veriq evaluate
    craft analysis list                 全 analysis 一覧
    craft analysis run <sub> <name>     analysis 実行
    craft history [PATH] [--limit N]    git log
    craft diff <FROM> <TO> [PATH]       git diff
    craft gen-stubs [--check]           Component/Config の .pyi stub 生成
    craft init system <name>         system 雛形生成
"""

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from core.discovery import discover_systems

# Typer サブアプリ
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Craft — Concept Registry for Automated spacecraFT design",
)
schema_app = typer.Typer(no_args_is_help=True, help="Pydantic Schema 配信")
analysis_app = typer.Typer(no_args_is_help=True, help="@analysis 関数の実行")
init_app = typer.Typer(no_args_is_help=True, help="プロジェクト/サブシステム雛形生成")
spec_app = typer.Typer(no_args_is_help=True, help="MultiInstance の shared spec 操作")
runs_app = typer.Typer(no_args_is_help=True, help="verification run history")
app.add_typer(schema_app, name="schema")
app.add_typer(analysis_app, name="analysis")
app.add_typer(init_app, name="init")
app.add_typer(spec_app, name="spec")
app.add_typer(runs_app, name="runs")


def _bootstrap() -> None:
    """全 system を import → registry 確定。"""
    discover_systems()


def _print_json(obj: Any) -> None:
    typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=_jsonable))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


# ─── history / diff ─────────────────────────────────────────────────


@app.command("history")
def history_cmd(
    path: str | None = typer.Argument(None, help="対象 path (省略時はリポジトリ全体)"),
    limit: int = typer.Option(20, "--limit", "-n", min=0, help="最大件数"),
) -> None:
    """git log 由来の変更履歴を表示。"""
    from core.history import GitError, GitRefNotFound, git_log

    try:
        entries = git_log(path, limit=limit)
    except GitRefNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    except GitError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    _print_json(
        {
            "path": path,
            "entries": [
                {
                    "sha": entry.sha,
                    "author": entry.author,
                    "date": entry.date,
                    "message": entry.message,
                }
                for entry in entries
            ],
        }
    )


@app.command("diff")
def diff_cmd(
    from_sha: str = typer.Argument(..., help="比較元 commit/ref"),
    to_sha: str = typer.Argument(..., help="比較先 commit/ref"),
    path: str | None = typer.Argument(None, help="対象 path (省略時は全体)"),
) -> None:
    """2 点間の git diff を表示。"""
    from core.history import GitError, GitRefNotFound, git_diff

    try:
        typer.echo(git_diff(from_sha, to_sha, path), nl=False)
    except GitRefNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    except GitError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e


# ─── schema ──────────────────────────────────────────────────────────


@schema_app.command("list")
def schema_list() -> None:
    """登録済み system / component を一覧表示。"""
    _bootstrap()
    from schema import default_registry

    out: dict[str, list[dict[str, Any]]] = {}
    for c in default_registry.components():
        out.setdefault(c.system, []).append(
            {
                "name": c.name,
                "plural": c.plural,
                "cardinality": c.cardinality,
                "traits": list(c.traits),
            }
        )
    _print_json(out)


@schema_app.command("show")
def schema_show(system: str, component: str) -> None:
    """単一 component の JSON Schema (Entry model) を表示。"""
    _bootstrap()
    from schema import default_registry

    defn = default_registry.component_or_none(system, component)
    if defn is None:
        typer.echo(f"Error: component '{system}.{component}' not found", err=True)
        raise typer.Exit(code=1)
    _print_json(defn.entry.model_json_schema())


# ─── get ─────────────────────────────────────────────────────────────


@app.command("get")
def get(
    system: str,
    component: str,
    instance: str | None = typer.Argument(None),
) -> None:
    """インスタンス取得（instance 省略時は全インスタンス）。"""
    _bootstrap()
    from core.instances import (
        InstanceNotFound,
        get_instance,
        list_instances,
    )

    if instance is None:
        _print_json(list_instances(system, component))
        return
    try:
        payload, etag = get_instance(system, component, instance)
    except InstanceNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(f"# ETag: {etag}")
    _print_json(payload)


# ─── CRUD: create / put / patch / delete ────────────────────────────


def _load_payload(data_path: Path | None, json_str: str | None) -> dict[str, Any]:
    """`--data <path>` (TOML/JSON) または `--json <str>` または stdin から payload を読む。"""
    if data_path is not None and json_str is not None:
        raise typer.BadParameter("--data と --json は同時に指定できません")
    if data_path is not None:
        if not data_path.exists():
            raise typer.BadParameter(f"file not found: {data_path}")
        suffix = data_path.suffix.lower()
        if suffix == ".toml":
            from core.toml_io import read_toml

            return read_toml(data_path)
        if suffix == ".json":
            return _parse_json_strict(data_path.read_text(encoding="utf-8"), source=str(data_path))
        raise typer.BadParameter(f"unsupported extension: {suffix} (expected .toml or .json)")
    if json_str is not None:
        return _parse_json_strict(json_str, source="--json")
    raw = sys.stdin.read()
    if not raw.strip():
        raise typer.BadParameter("payload が空です（--data / --json / stdin のいずれかを指定）")
    return _parse_json_strict(raw, source="stdin")


def _parse_json_strict(raw: str, *, source: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"{source} の JSON 解析に失敗: {e}") from e
    if not isinstance(obj, dict):
        raise typer.BadParameter(f"{source} の payload は object である必要があります")
    return obj


def _format_validation_error(err: ValidationError) -> str:
    lines = ["ValidationError:"]
    for e in err.errors():
        loc = ".".join(str(p) for p in e.get("loc", ()))
        msg = e.get("msg", "")
        lines.append(f"  - {loc}: {msg}")
    return "\n".join(lines)


def _resolve_instance_etag(system: str, component: str, instance: str) -> str:
    """`--etag` 省略時に現在の instance ETag を取得する。"""
    from core.instances import InstanceNotFound, get_instance

    try:
        _, etag = get_instance(system, component, instance)
    except InstanceNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    return etag


def _resolve_shared_spec_etag(system: str, component: str) -> str:
    from core.instances import (
        InstanceNotFound,
        SingletonNotInstanceable,
        get_shared_spec,
    )

    try:
        _, etag = get_shared_spec(system, component)
    except (InstanceNotFound, SingletonNotInstanceable) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    return etag


@app.command("create")
def create_cmd(
    system: str,
    component: str,
    instance: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON payload file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON payload (inline)"),
) -> None:
    """新規インスタンス作成（MultiInstance のみ）。"""
    _bootstrap()
    from core.instances import (
        InstanceAlreadyExists,
        InstanceNotFound,
        SharedSpecConflict,
        SingletonNotInstanceable,
        create_instance,
    )

    payload = _load_payload(data, json_str)
    try:
        view, etag = create_instance(system, component, instance, payload)
    except (
        InstanceAlreadyExists,
        SingletonNotInstanceable,
        SharedSpecConflict,
        InstanceNotFound,
    ) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"# ETag: {etag}")
    _print_json(view)


@app.command("put")
def put_cmd(
    system: str,
    component: str,
    instance: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON payload file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON payload (inline)"),
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag (省略時は GET で取得)"),
) -> None:
    """インスタンス全置換。"""
    _bootstrap()
    from core.instances import (
        InstanceNotFound,
        SharedSpecConflict,
        SingletonNotInstanceable,
        replace_instance,
    )

    payload = _load_payload(data, json_str)
    resolved_etag = (
        etag if etag is not None else _resolve_instance_etag(system, component, instance)
    )
    try:
        view, new_etag = replace_instance(
            system, component, instance, payload, expected_etag=resolved_etag
        )
    except (InstanceNotFound, SingletonNotInstanceable, SharedSpecConflict) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"# ETag: {new_etag}")
    _print_json(view)


@app.command("patch")
def patch_cmd(
    system: str,
    component: str,
    instance: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON delta file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON delta (inline)"),
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag (省略時は GET で取得)"),
) -> None:
    """インスタンス部分更新（deep merge）。"""
    _bootstrap()
    from core.instances import (
        InstanceNotFound,
        SharedSpecConflict,
        SingletonNotInstanceable,
        patch_instance,
    )

    delta = _load_payload(data, json_str)
    resolved_etag = (
        etag if etag is not None else _resolve_instance_etag(system, component, instance)
    )
    try:
        view, new_etag = patch_instance(
            system, component, instance, delta, expected_etag=resolved_etag
        )
    except (InstanceNotFound, SingletonNotInstanceable, SharedSpecConflict) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"# ETag: {new_etag}")
    _print_json(view)


@app.command("delete")
def delete_cmd(
    system: str,
    component: str,
    instance: str,
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag (省略時は GET で取得)"),
) -> None:
    """インスタンス削除（MultiInstance のみ）。"""
    _bootstrap()
    from core.instances import (
        InstanceNotFound,
        SingletonNotInstanceable,
        delete_instance,
    )

    resolved_etag = (
        etag if etag is not None else _resolve_instance_etag(system, component, instance)
    )
    try:
        delete_instance(system, component, instance, expected_etag=resolved_etag)
    except (InstanceNotFound, SingletonNotInstanceable) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"Deleted {system}.{component}.{instance}")


# ─── shared spec ────────────────────────────────────────────────────


@spec_app.command("get")
def spec_get(system: str, component: str) -> None:
    """MultiInstance の shared spec を取得。"""
    _bootstrap()
    from core.instances import (
        InstanceNotFound,
        SingletonNotInstanceable,
        get_shared_spec,
    )

    try:
        spec, etag = get_shared_spec(system, component)
    except (InstanceNotFound, SingletonNotInstanceable) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"# ETag: {etag}")
    _print_json(spec)


@spec_app.command("set")
def spec_set(
    system: str,
    component: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON payload file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON payload (inline)"),
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag (省略時は GET で取得)"),
) -> None:
    """shared spec を更新。"""
    _bootstrap()
    from core.instances import (
        InstanceNotFound,
        SingletonNotInstanceable,
        set_shared_spec,
    )

    payload = _load_payload(data, json_str)
    # 既存 shared spec があるなら etag を要求 (set_shared_spec の挙動に合わせる)
    resolved_etag = etag
    if resolved_etag is None:
        from core.instances import get_shared_spec

        try:
            _, resolved_etag = get_shared_spec(system, component)
        except InstanceNotFound:
            resolved_etag = None  # まだ無いので etag 不要
        except SingletonNotInstanceable as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from e

    try:
        new_spec, new_etag = set_shared_spec(
            system, component, payload, expected_etag=resolved_etag
        )
    except (InstanceNotFound, SingletonNotInstanceable) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"# ETag: {new_etag}")
    _print_json(new_spec)


# ─── merge ───────────────────────────────────────────────────────────


@app.command("merge")
def merge_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="書き込まず stdout に出力"),
    check: bool = typer.Option(False, "--check", help="lock が古ければ exit 1 (CI 用)"),
) -> None:
    """全 systems/*/data.toml を generated/merged.toml に統合。"""
    _bootstrap()
    from core.merge import is_merge_stale, merge

    if check:
        stale = is_merge_stale()
        if stale:
            typer.echo("Stale: merged.lock は元 data.toml と一致しません。", err=True)
            raise typer.Exit(code=1)
        typer.echo("OK: merged.toml は最新です。")
        return

    result, merged_dict = merge(dry_run=dry_run)
    if dry_run:
        _print_json(merged_dict)
    else:
        typer.echo(f"Wrote {result.output_path}")
        typer.echo(f"Subsystems: {', '.join(result.systems)}")


# ─── scaffold ────────────────────────────────────────────────────────


@app.command("scaffold")
def scaffold_cmd(
    system: str | None = typer.Argument(None, help="対象 system (省略時は全件)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    format_only: bool = typer.Option(
        False, "--format-only", help="既存値を変えず順序・コメントのみ整形"
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="既存値を default に戻す（破壊的）"),
) -> None:
    """registry → data.toml 雛形生成 (add-missing, 既存値保持)。"""
    _bootstrap()
    from core.scaffold import scaffold_all, scaffold_system

    if format_only and overwrite:
        typer.echo(
            "Warning: --format-only and --overwrite are mutually exclusive; --format-only takes precedence.",
            err=True,
        )
    mode = "format-only" if format_only else ("overwrite" if overwrite else "add-missing")

    if system is None:
        results = scaffold_all(dry_run=dry_run, mode=mode)
    else:
        try:
            r, _ = scaffold_system(system, dry_run=dry_run, mode=mode)
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from e
        results = [r]

    for r in results:
        marker = "(dry-run)" if dry_run else ""
        typer.echo(
            f"{r.system}: added={len(r.added_paths)} warnings={len(r.removed_warnings)} {marker}"
        )
        for p in r.added_paths:
            typer.echo(f"  + {p}")
        for w in r.removed_warnings:
            typer.echo(f"  ! unknown: {w}")


# ─── verify ──────────────────────────────────────────────────────────


@app.command("verify")
def verify_cmd(
    fail_on_verify: bool = typer.Option(
        True,
        "--fail-on-verify/--no-fail-on-verify",
        help="verification が 1 つでも False なら exit 1",
    ),
    async_: bool = typer.Option(False, "--async", help="job_id を発行して即終了"),
) -> None:
    """merge → veriq evaluate_project を実行。"""
    _bootstrap()
    if async_:
        from core.jobs import job_to_dict, submit_verify_job

        _print_json(job_to_dict(submit_verify_job()))
        return

    from core.verify import run_verify_core

    result = run_verify_core()

    any_failed = False
    for scope in result["scopes"].values():
        for node in scope["calculations"]:
            typer.echo(f"  CALC {node['path']}  =  {node['value']}")
        for node in scope["verifications"]:
            mark = "✓" if node["value"] else "✗"
            typer.echo(f"  VERI {mark} {node['path']}  =  {node['value']}")
            if node["value"] is False:
                any_failed = True

    typer.echo(
        f"success={result['success']}, errors={len(result['errors'])}, run_id={result['run_id']}"
    )
    if any_failed and fail_on_verify:
        raise typer.Exit(code=1)


# ─── runs ────────────────────────────────────────────────────────────


@runs_app.command("list")
def runs_list(limit: int = typer.Option(20, "--limit", "-n", min=0, help="最大件数")) -> None:
    """verification run 一覧を新しい順に表示。"""
    from core.runs import list_runs, run_to_dict

    _print_json({"runs": [run_to_dict(run) for run in list_runs(limit=limit)]})


@runs_app.command("show")
def runs_show(run_id: str) -> None:
    """単一 verification run の詳細を表示。"""
    from core.runs import get_run, run_to_dict

    run = get_run(run_id)
    if run is None:
        typer.echo(f"Error: run '{run_id}' not found", err=True)
        raise typer.Exit(code=1)
    _print_json(run_to_dict(run))


@runs_app.command("latest")
def runs_latest() -> None:
    """最新 verification run を表示。"""
    from core.runs import get_run, latest_run_id, run_to_dict

    run_id = latest_run_id()
    if run_id is None:
        typer.echo("Error: no runs found", err=True)
        raise typer.Exit(code=1)
    run = get_run(run_id)
    if run is None:
        typer.echo(f"Error: run '{run_id}' not found", err=True)
        raise typer.Exit(code=1)
    _print_json(run_to_dict(run))


@runs_app.command("artifact")
def runs_artifact(run_id: str, name: str) -> None:
    """指定 artifact の中身を stdout に出力。"""
    from core.runs import get_run_artifact

    content = get_run_artifact(run_id, name)
    if content is None:
        typer.echo(f"Error: artifact '{name}' not found for run '{run_id}'", err=True)
        raise typer.Exit(code=1)
    sys.stdout.buffer.write(content)


# ─── analysis ────────────────────────────────────────────────────────


@analysis_app.command("list")
def analysis_list() -> None:
    """登録済み @analysis 関数を一覧。"""
    _bootstrap()
    from schema import default_registry

    items = [
        {
            "name": a.name,
            "system": a.system,
            "verify": a.verify,
            "desc": a.desc,
        }
        for a in default_registry.analyses()
    ]
    _print_json(items)


@analysis_app.command("run")
def analysis_run(
    system: str = typer.Argument(..., help="ad-hoc は '_'"),
    name: str = typer.Argument(...),
    payload_json: str | None = typer.Option(
        None, "--payload", "-p", help="JSON payload (ad-hoc analysis のみ)"
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="ad-hoc cache をスキップ"),
) -> None:
    """analysis を実行（veriq 連携 or ad-hoc）。"""
    _bootstrap()
    sub = None if system == "_" else system
    from schema import default_registry

    adef = default_registry.analysis_or_none(sub, name)
    if adef is None:
        typer.echo(f"Error: analysis '{system}.{name}' not found", err=True)
        raise typer.Exit(code=1)

    payload = json.loads(payload_json) if payload_json else {}

    if adef.system is None:
        import inspect

        from core.analysis_cache import (
            code_version_for_func,
            compute_cache_key,
            get_cached,
            put_cached,
        )

        sig = inspect.signature(adef.func)
        bound = sig.bind_partial(**payload)
        bound.apply_defaults()
        inputs = dict(bound.arguments)
        cache_key: str | None = None
        if adef.cache and not no_cache:
            code_version = code_version_for_func(adef.func)
            cache_key = compute_cache_key(adef.name, code_version, inputs)
            cached = get_cached(adef.name, cache_key)
            if cached is not None:
                _print_json({"value": cached.get("value"), "cache_hit": True})
                return
        value = adef.func(*bound.args, **bound.kwargs)
        json_value = _jsonable(value)
        if cache_key is not None:
            put_cached(adef.name, cache_key, {"value": json_value})
        output = {"value": json_value}
        if adef.cache:
            output["cache_hit"] = False
        _print_json(output)
        return

    # veriq 経由
    import veriq as vq

    from core.merge import MERGED_TOML
    from core.merge import merge as merge_func

    project = vq.Project("Craft")
    for s in sorted(default_registry.systems()):
        mod = importlib.import_module(f"systems.{s}.scope")
        scope = getattr(mod, s, None)
        if scope is not None:
            project.add_scope(scope)
    merge_func()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    tree = result.get_scope_tree(adef.system)
    if tree is None:
        _print_json({"value": None})
        return
    nodes = tree.verifications if adef.verify else tree.calculations
    prefix = "?" if adef.verify else "@"
    for node in nodes:
        if str(node.path).endswith(f"{prefix}{adef.name}"):
            _print_json({"value": _jsonable(node.value)})
            return
    _print_json({"value": None})


# ─── gen-stubs ───────────────────────────────────────────────────────


@app.command("gen-stubs")
def gen_stubs_cmd(
    check: bool = typer.Option(
        False,
        "--check",
        help="既存 .pyi が古ければ exit 1 (書き込みなし、CI 用)",
    ),
) -> None:
    """各 system に `_stubs.pyi` を生成する。"""
    _bootstrap()
    from schema.stubgen import check_stubs, generate_stubs

    if check:
        mismatches = check_stubs()
        if mismatches:
            typer.echo("Stale stubs detected:", err=True)
            for path, diff in mismatches:
                typer.echo(f"  {path}", err=True)
                if diff:
                    typer.echo(diff, err=True)
            raise typer.Exit(code=1)
        typer.echo("OK: all stubs are up to date.")
        return

    written = generate_stubs()
    for path in written:
        typer.echo(f"Wrote {path}")

    if written:
        import subprocess

        subprocess.run(
            ["uv", "run", "ruff", "format", *[str(p) for p in written]],
            check=True,
        )


# ─── init ────────────────────────────────────────────────────────────


@init_app.command("system")
def init_subsystem(
    name: str,
    kind: str = typer.Option(
        "hardware",
        "--kind",
        help="hardware | config-only | default (= 空のスケルトン)",
    ),
) -> None:
    """新しい system ディレクトリ雛形を生成。"""
    from cli import templates

    target = Path("systems") / name
    if target.exists():
        typer.echo(f"Error: {target} already exists", err=True)
        raise typer.Exit(code=1)

    templates.create_subsystem(target, name=name, kind=kind)
    typer.echo(f"Created {target}/ ({kind})")
    typer.echo("Next steps:")
    typer.echo(f"  1. edit systems/{name}/components.py (or configs.py)")
    typer.echo(f"  2. craft scaffold {name}")
    typer.echo(f"  3. fill values in systems/{name}/data.toml")
    typer.echo("  4. craft verify")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
