"""Maintenance commands: history, diff, gen-stubs, init."""

from pathlib import Path

import typer

from cli._io import _print_json

init_app = typer.Typer(no_args_is_help=True, help="プロジェクト/サブシステム雛形生成")


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


def gen_stubs_cmd(
    check: bool = typer.Option(
        False,
        "--check",
        help="既存 .pyi が古ければ exit 1 (書き込みなし、CI 用)",
    ),
) -> None:
    """各 system に `_stubs.pyi` を生成する。"""
    from core.discovery import discover_systems
    from core.stubgen import check_stubs, generate_stubs

    discover_systems()
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
