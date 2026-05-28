"""merge / scaffold / verify / validate コマンド。"""

from dataclasses import asdict
from pathlib import Path
from typing import Any

import typer

from craft.cli._io import _load_payload, _print_json
from craft.core.discovery import discover_systems

validate_app = typer.Typer(no_args_is_help=True, help="Pydantic schema validation only")


def _bootstrap() -> None:
    discover_systems()


def _load_validation_payload(
    data: Path | None,
    json_str: str | None,
    stdin: bool,
) -> dict[str, Any]:
    if stdin and (data is not None or json_str is not None):
        raise typer.BadParameter("--stdin は --data / --json と同時に指定できません")
    return _load_payload(data, json_str)


def merge_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="書き込まず stdout に出力"),
    check: bool = typer.Option(False, "--check", help="lock が古ければ exit 1 (CI 用)"),
) -> None:
    """全 systems/*/data.toml を generated/merged.toml に統合。"""
    _bootstrap()
    from craft.core.pipeline.merge import is_merge_stale, merge

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
    from craft.core.pipeline.scaffold import scaffold_all, scaffold_system

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


def verify_cmd(
    fail_on_verify: bool = typer.Option(
        False,
        "--fail-on-verify/--no-fail-on-verify",
        help="verification が 1 つでも False なら exit 1",
    ),
    async_: bool = typer.Option(False, "--async", help="job_id を発行して即終了"),
) -> None:
    """merge → veriq evaluate_project を実行。"""
    _bootstrap()
    if async_:
        from craft.core.persistence.jobs import job_to_dict, submit_verify_job

        _print_json(job_to_dict(submit_verify_job()))
        return

    from craft.core.pipeline.verify import run_verify_core

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


@validate_app.command("component")
def validate_component_cmd(
    system: str,
    component: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON payload file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON payload (inline)"),
    stdin: bool = typer.Option(False, "--stdin", help="Read JSON payload from stdin"),
) -> None:
    """Component payload を副作用なしで Pydantic 検証する。"""
    _bootstrap()
    from craft.core.instances import InstanceNotFound
    from craft.core.surface_ops.validation import validate_component_payload

    payload = _load_validation_payload(data, json_str, stdin)
    try:
        result = validate_component_payload(system, component, payload)
    except InstanceNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    _print_json(asdict(result))
    if not result.ok:
        raise typer.Exit(code=1)


@validate_app.command("config")
def validate_config_cmd(
    system: str,
    name: str,
    data: Path | None = typer.Option(None, "--data", help="TOML or JSON payload file"),
    json_str: str | None = typer.Option(None, "--json", help="JSON payload (inline)"),
    stdin: bool = typer.Option(False, "--stdin", help="Read JSON payload from stdin"),
) -> None:
    """Config payload を副作用なしで Pydantic 検証する。"""
    _bootstrap()
    from craft.core.instances import InstanceNotFound
    from craft.core.surface_ops.validation import validate_config_payload

    payload = _load_validation_payload(data, json_str, stdin)
    try:
        result = validate_config_payload(system, name, payload)
    except InstanceNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    _print_json(asdict(result))
    if not result.ok:
        raise typer.Exit(code=1)
