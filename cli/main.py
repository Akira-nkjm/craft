"""Craft CLI — Typer ベース。core / schema を直接 import する offline モード。

主要コマンド:
    craft schema list                   全 component の一覧
    craft schema show <sub> <comp>      JSON Schema
    craft get <sub> <comp> [<inst>]     インスタンス取得
    craft merge [--check] [--dry-run]   merged.toml 再生成
    craft scaffold [<sub>] [--dry-run]  data.toml 雛形生成
    craft verify                        merge → veriq evaluate
    craft analysis list                 全 analysis 一覧
    craft analysis run <sub> <name>     analysis 実行
    craft init subsystem <name>         subsystem 雛形生成
"""

import importlib
import json
from pathlib import Path
from typing import Any

import typer

from core.discovery import discover_subsystems

# Typer サブアプリ
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Craft — Concept Registry for Automated spacecraFT design",
)
schema_app = typer.Typer(no_args_is_help=True, help="Pydantic Schema 配信")
analysis_app = typer.Typer(no_args_is_help=True, help="@analysis 関数の実行")
init_app = typer.Typer(no_args_is_help=True, help="プロジェクト/サブシステム雛形生成")
app.add_typer(schema_app, name="schema")
app.add_typer(analysis_app, name="analysis")
app.add_typer(init_app, name="init")


def _bootstrap() -> None:
    """全 subsystem を import → registry 確定。"""
    discover_subsystems()


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


# ─── schema ──────────────────────────────────────────────────────────


@schema_app.command("list")
def schema_list() -> None:
    """登録済み subsystem / component を一覧表示。"""
    _bootstrap()
    from schema import default_registry

    out: dict[str, list[dict[str, Any]]] = {}
    for c in default_registry.components():
        out.setdefault(c.subsystem, []).append(
            {
                "name": c.name,
                "plural": c.plural,
                "cardinality": c.cardinality,
                "traits": list(c.traits),
            }
        )
    _print_json(out)


@schema_app.command("show")
def schema_show(subsystem: str, component: str) -> None:
    """単一 component の JSON Schema (Entry model) を表示。"""
    _bootstrap()
    from schema import default_registry

    defn = default_registry.component_or_none(subsystem, component)
    if defn is None:
        typer.echo(f"Error: component '{subsystem}.{component}' not found", err=True)
        raise typer.Exit(code=1)
    _print_json(defn.entry.model_json_schema())


# ─── get ─────────────────────────────────────────────────────────────


@app.command("get")
def get(
    subsystem: str,
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
        _print_json(list_instances(subsystem, component))
        return
    try:
        payload, etag = get_instance(subsystem, component, instance)
    except InstanceNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(f"# ETag: {etag}")
    _print_json(payload)


# ─── merge ───────────────────────────────────────────────────────────


@app.command("merge")
def merge_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="書き込まず stdout に出力"),
    check: bool = typer.Option(False, "--check", help="lock が古ければ exit 1 (CI 用)"),
) -> None:
    """全 subsystems/*/data.toml を generated/merged.toml に統合。"""
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
        typer.echo(f"Subsystems: {', '.join(result.subsystems)}")


# ─── scaffold ────────────────────────────────────────────────────────


@app.command("scaffold")
def scaffold_cmd(
    subsystem: str | None = typer.Argument(None, help="対象 subsystem (省略時は全件)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """registry → data.toml 雛形生成 (add-missing, 既存値保持)。"""
    _bootstrap()
    from core.scaffold import scaffold_all, scaffold_subsystem

    if subsystem is None:
        results = scaffold_all(dry_run=dry_run)
    else:
        try:
            r, _ = scaffold_subsystem(subsystem, dry_run=dry_run)
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1) from e
        results = [r]

    for r in results:
        marker = "(dry-run)" if dry_run else ""
        typer.echo(
            f"{r.subsystem}: added={len(r.added_paths)} warnings={len(r.removed_warnings)} {marker}"
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
) -> None:
    """merge → veriq evaluate_project を実行。"""
    _bootstrap()
    import veriq as vq

    from core.merge import MERGED_TOML, merge
    from schema import default_registry

    project = vq.Project("Craft")
    for sub in sorted(default_registry.subsystems()):
        mod = importlib.import_module(f"subsystems.{sub}.scope")
        scope = getattr(mod, sub, None)
        if scope is None:
            continue
        project.add_scope(scope)

    merge()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)

    any_failed = False
    for scope_name in result.scopes:
        tree = result.get_scope_tree(scope_name)
        if tree is None:
            continue
        for node in tree.calculations:
            typer.echo(f"  CALC {node.path}  =  {node.value}")
        for node in tree.verifications:
            mark = "✓" if node.value else "✗"
            typer.echo(f"  VERI {mark} {node.path}  =  {node.value}")
            if node.value is False:
                any_failed = True

    typer.echo(f"success={result.success}, errors={len(result.errors)}")
    if any_failed and fail_on_verify:
        raise typer.Exit(code=1)


# ─── analysis ────────────────────────────────────────────────────────


@analysis_app.command("list")
def analysis_list() -> None:
    """登録済み @analysis 関数を一覧。"""
    _bootstrap()
    from schema import default_registry

    items = [
        {
            "name": a.name,
            "subsystem": a.subsystem,
            "verify": a.verify,
            "desc": a.desc,
        }
        for a in default_registry.analyses()
    ]
    _print_json(items)


@analysis_app.command("run")
def analysis_run(
    subsystem: str = typer.Argument(..., help="ad-hoc は '_'"),
    name: str = typer.Argument(...),
    payload_json: str | None = typer.Option(
        None, "--payload", "-p", help="JSON payload (ad-hoc analysis のみ)"
    ),
) -> None:
    """analysis を実行（veriq 連携 or ad-hoc）。"""
    _bootstrap()
    sub = None if subsystem == "_" else subsystem
    from schema import default_registry

    adef = default_registry.analysis_or_none(sub, name)
    if adef is None:
        typer.echo(f"Error: analysis '{subsystem}.{name}' not found", err=True)
        raise typer.Exit(code=1)

    payload = json.loads(payload_json) if payload_json else {}

    if adef.subsystem is None:
        import inspect

        sig = inspect.signature(adef.func)
        bound = sig.bind_partial(**payload)
        bound.apply_defaults()
        value = adef.func(*bound.args, **bound.kwargs)
        _print_json({"value": _jsonable(value)})
        return

    # veriq 経由
    import veriq as vq

    from core.merge import MERGED_TOML
    from core.merge import merge as merge_func

    project = vq.Project("Craft")
    for s in sorted(default_registry.subsystems()):
        mod = importlib.import_module(f"subsystems.{s}.scope")
        scope = getattr(mod, s, None)
        if scope is not None:
            project.add_scope(scope)
    merge_func()
    model_data = vq.load_model_data_from_toml(project, MERGED_TOML)
    result = vq.evaluate_project(project, model_data)
    tree = result.get_scope_tree(adef.subsystem)
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


# ─── init ────────────────────────────────────────────────────────────


@init_app.command("subsystem")
def init_subsystem(
    name: str,
    kind: str = typer.Option(
        "hardware",
        "--kind",
        help="hardware | config-only | default (= 空のスケルトン)",
    ),
) -> None:
    """新しい subsystem ディレクトリ雛形を生成。"""
    from cli import templates

    target = Path("subsystems") / name
    if target.exists():
        typer.echo(f"Error: {target} already exists", err=True)
        raise typer.Exit(code=1)

    templates.create_subsystem(target, name=name, kind=kind)
    typer.echo(f"Created {target}/ ({kind})")
    typer.echo("Next steps:")
    typer.echo(f"  1. edit subsystems/{name}/components.py (or configs.py)")
    typer.echo(f"  2. craft scaffold {name}")
    typer.echo(f"  3. fill values in subsystems/{name}/data.toml")
    typer.echo("  4. craft verify")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
