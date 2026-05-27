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

from pathlib import Path

import typer
from pydantic import ValidationError

from cli._etag import _resolve_instance_etag
from cli._io import _format_validation_error, _load_payload, _print_json
from cli.commands.data import merge_cmd, scaffold_cmd, verify_cmd
from cli.commands.maintenance import diff_cmd, gen_stubs_cmd, history_cmd, init_app
from cli.commands.runs_analysis import analysis_app, runs_app
from cli.commands.schema import get, schema_app
from core.discovery import discover_systems
from core.errors import ETagMismatch, PreconditionRequired

# Typer サブアプリ
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Craft — Concept Registry for Automated spacecraFT design",
)
spec_app = typer.Typer(no_args_is_help=True, help="MultiInstance の shared spec 操作")
app.add_typer(schema_app, name="schema")
app.command("get")(get)
app.add_typer(analysis_app, name="analysis")
app.add_typer(init_app, name="init")
app.add_typer(spec_app, name="spec")
app.add_typer(runs_app, name="runs")
app.command("history")(history_cmd)
app.command("diff")(diff_cmd)
app.command("gen-stubs")(gen_stubs_cmd)

app.command("merge")(merge_cmd)
app.command("scaffold")(scaffold_cmd)
app.command("verify")(verify_cmd)


def _bootstrap() -> None:
    """全 system を import → registry 確定。"""
    discover_systems()


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
