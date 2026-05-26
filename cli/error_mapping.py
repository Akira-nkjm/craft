"""CLI surface: exit with error message when OperationResult is not ok."""

import typer

from core.operations import OperationResult


def exit_if_error(result: OperationResult) -> None:
    """Echo error to stderr and raise typer.Exit(1) if result.status is not 'ok'."""
    if result.status != "ok":
        typer.echo(f"Error: {result.error_message}", err=True)
        raise typer.Exit(code=1)
