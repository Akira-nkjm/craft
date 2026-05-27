import typer


def _resolve_instance_etag(system: str, component: str, instance: str) -> str:
    """`--etag` 省略時に現在の instance ETag を取得する。"""
    from craft.core.instances import InstanceNotFound, get_instance

    try:
        _, etag = get_instance(system, component, instance)
    except InstanceNotFound as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    return etag
