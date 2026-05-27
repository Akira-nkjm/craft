"""Instance CRUD (create/put/patch/delete) and shared-spec CLI commands."""

from pathlib import Path

import typer
from pydantic import ValidationError

from cli._etag import _resolve_instance_etag
from cli._io import _format_validation_error, _load_payload, _print_json
from core.discovery import discover_systems
from core.errors import ETagMismatch, PreconditionRequired

spec_app = typer.Typer(no_args_is_help=True, help="MultiInstance の shared spec 操作")


def _bootstrap() -> None:
    discover_systems()


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
    from core.surface_ops.operations import create_component_op

    payload = _load_payload(data, json_str)
    try:
        result = create_component_op(system, component, instance, payload)
    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from e
    exit_if_error(result)
    typer.echo(f"# ETag: {result.etag}")
    _print_json(result.payload)


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
    from core.surface_ops.concurrency import ETagMode, resolve_expected_etag
    from core.surface_ops.operations import replace_component_op

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
    from core.surface_ops.concurrency import ETagMode, resolve_expected_etag
    from core.surface_ops.operations import patch_component_op

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
    from core.surface_ops.concurrency import ETagMode, resolve_expected_etag
    from core.surface_ops.operations import delete_component_op

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
    from core.instances import (
        InstanceNotFound,
        SingletonNotInstanceable,
        get_shared_spec,
        set_shared_spec,
    )
    from core.surface_ops.concurrency import ETagMode, resolve_expected_etag

    payload = _load_payload(data, json_str)
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
        resolved_etag = etag
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
