"""OperationResult → Typer CLI exit."""

import typer

from core.operations import OperationResult


def apply_cli_result(result: OperationResult) -> None:
    """Print error to stderr and raise typer.Exit(1) for non-ok results."""
    if result.status == "ok":
        return
    typer.echo(f"Error: {result.error_code}", err=True)
    raise typer.Exit(code=1)
