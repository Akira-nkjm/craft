"""schema サブコマンドと get コマンド。"""

from typing import Any

import typer

from craft.cli._io import _print_json
from craft.core.discovery import discover_systems

schema_app = typer.Typer(no_args_is_help=True, help="Pydantic Schema 配信")
systems_app = typer.Typer(no_args_is_help=True, help="登録済み system の一覧")


@systems_app.command("list")
def systems_list() -> None:
    """登録済み system 名を一覧表示。"""
    discover_systems()
    from craft.core.surface_ops.introspection import list_systems_summary

    _print_json(list_systems_summary())


@schema_app.command("list")
def schema_list() -> None:
    """登録済み system / component を一覧表示。"""
    discover_systems()
    from craft.core.surface_ops.introspection import list_components_summary

    out: dict[str, list[dict[str, Any]]] = {}
    for s in list_components_summary():
        out.setdefault(s.system, []).append(
            {
                "name": s.name,
                "plural": s.plural,
                "cardinality": s.cardinality,
                "traits": list(s.traits),
            }
        )
    _print_json(out)


@schema_app.command("show")
def schema_show(system: str, component: str) -> None:
    """単一 component の JSON Schema (Entry model) を表示。"""
    discover_systems()
    from craft.schema import default_registry

    defn = default_registry.component_or_none(system, component)
    if defn is None:
        typer.echo(f"Error: component '{system}.{component}' not found", err=True)
        raise typer.Exit(code=1)
    _print_json(defn.entry.model_json_schema())


def get(
    system: str,
    component: str,
    instance: str | None = typer.Argument(None),
) -> None:
    """インスタンス取得（instance 省略時は全インスタンス）。"""
    discover_systems()
    from craft.core.instances import (
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
