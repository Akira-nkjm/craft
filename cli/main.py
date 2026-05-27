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

import json
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from cli._etag import _resolve_instance_etag
from cli._io import _format_validation_error, _load_payload, _print_json
from cli.commands.schema import get, schema_app
from core.discovery import discover_systems
from core.errors import ETagMismatch, PreconditionRequired

# Typer サブアプリ
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Craft — Concept Registry for Automated spacecraFT design",
)
analysis_app = typer.Typer(no_args_is_help=True, help="@analysis 関数の実行")
init_app = typer.Typer(no_args_is_help=True, help="プロジェクト/サブシステム雛形生成")
spec_app = typer.Typer(no_args_is_help=True, help="MultiInstance の shared spec 操作")
runs_app = typer.Typer(no_args_is_help=True, help="verification run history")
app.add_typer(schema_app, name="schema")
app.command("get")(get)
app.add_typer(analysis_app, name="analysis")
app.add_typer(init_app, name="init")
app.add_typer(spec_app, name="spec")
app.add_typer(runs_app, name="runs")


def _bootstrap() -> None:
    """全 system を import → registry 確定。"""
    discover_systems()


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


# ─── CRUD: create / put / patch / delete ────────────────────────────


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
    from cli.error_mapping import exit_if_error
    from core.operations import create_component_op

    payload = _load_payload(data, json_str)
    try:
        result = create_component_op(system, component, instance, payload)
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e
    exit_if_error(result)
    typer.echo(f"# ETag: {result.etag}")
    _print_json(result.payload)


@app.command("put")
def put_cmd(
    system: str,
    component: str,
    instance: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON payload file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON payload (inline)"),
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag"),
    auto_etag: bool = typer.Option(
        False, "--auto-etag", help="ETag 省略時に GET で自動取得（楽観ロック無効化に注意）"
    ),
) -> None:
    """インスタンス全置換。"""
    _bootstrap()
    from cli.error_mapping import exit_if_error
    from core.concurrency import ETagMode, resolve_expected_etag
    from core.operations import replace_component_op

    payload = _load_payload(data, json_str)
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: _resolve_instance_etag(system, component, instance)
        )
    except PreconditionRequired as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    try:
        result = replace_component_op(system, component, instance, payload, if_match=resolved_etag)
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e
    exit_if_error(result)
    typer.echo(f"# ETag: {result.etag}")
    _print_json(result.payload)


@app.command("patch")
def patch_cmd(
    system: str,
    component: str,
    instance: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON delta file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON delta (inline)"),
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag"),
    auto_etag: bool = typer.Option(
        False, "--auto-etag", help="ETag 省略時に GET で自動取得（楽観ロック無効化に注意）"
    ),
) -> None:
    """インスタンス部分更新（deep merge）。"""
    _bootstrap()
    from cli.error_mapping import exit_if_error
    from core.concurrency import ETagMode, resolve_expected_etag
    from core.operations import patch_component_op

    delta = _load_payload(data, json_str)
    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: _resolve_instance_etag(system, component, instance)
        )
    except PreconditionRequired as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    try:
        result = patch_component_op(system, component, instance, delta, if_match=resolved_etag)
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e
    exit_if_error(result)
    typer.echo(f"# ETag: {result.etag}")
    _print_json(result.payload)


@app.command("delete")
def delete_cmd(
    system: str,
    component: str,
    instance: str,
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag"),
    auto_etag: bool = typer.Option(
        False, "--auto-etag", help="ETag 省略時に GET で自動取得（楽観ロック無効化に注意）"
    ),
) -> None:
    """インスタンス削除（MultiInstance のみ）。"""
    _bootstrap()
    from cli.error_mapping import exit_if_error
    from core.concurrency import ETagMode, resolve_expected_etag
    from core.operations import delete_component_op

    mode: ETagMode = "auto" if auto_etag else "required"
    try:
        resolved_etag = resolve_expected_etag(
            etag, mode, fetch=lambda: _resolve_instance_etag(system, component, instance)
        )
    except PreconditionRequired as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    result = delete_component_op(system, component, instance, if_match=resolved_etag)
    exit_if_error(result)
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
    etag: str | None = typer.Option(None, "--etag", help="If-Match ETag"),
    auto_etag: bool = typer.Option(
        False, "--auto-etag", help="ETag 省略時に GET で自動取得（楽観ロック無効化に注意）"
    ),
) -> None:
    """shared spec を更新。"""
    _bootstrap()
    from core.concurrency import ETagMode, resolve_expected_etag
    from core.instances import (
        InstanceNotFound,
        SingletonNotInstanceable,
        get_shared_spec,
        set_shared_spec,
    )

    payload = _load_payload(data, json_str)
    # spec が既に存在する場合のみ ETag policy を適用
    # 存在しない場合は新規作成のため etag 不要
    resolved_etag: str | None
    try:
        _, fetched_etag = get_shared_spec(system, component)
        mode: ETagMode = "auto" if auto_etag else "required"
        try:
            resolved_etag = resolve_expected_etag(etag, mode, fetch=lambda: fetched_etag)
        except PreconditionRequired as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from e
    except InstanceNotFound:
        resolved_etag = etag  # 新規作成: etag 不要
    except SingletonNotInstanceable as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    try:
        new_spec, new_etag = set_shared_spec(
            system, component, payload, expected_etag=resolved_etag
        )
    except (ETagMismatch, PreconditionRequired) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
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
            "Warning: --format-only and --overwrite are mutually exclusive; "
            "--format-only takes precedence.",
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
    from core.introspection import list_analyses_summary

    items = [
        {
            "name": s.name,
            "system": s.system,
            "verify": s.verify,
            "desc": s.desc,
        }
        for s in list_analyses_summary()
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
    payload = json.loads(payload_json) if payload_json else {}

    from core.analysis_runner import AnalysisArgumentError, AnalysisNotFound
    from core.analysis_runner import run_analysis as _run_analysis

    try:
        result = _run_analysis(sub, name, payload, use_cache=not no_cache)
    except AnalysisNotFound:
        typer.echo(f"Error: analysis '{system}.{name}' not found", err=True)
        raise typer.Exit(code=1) from None
    except AnalysisArgumentError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None

    output: dict[str, Any] = {"value": result.value}
    if result.cache_hit is not None:
        output["cache_hit"] = result.cache_hit
    _print_json(output)


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
    from core.stubgen import check_stubs, generate_stubs

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
