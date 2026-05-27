"""runs / analysis サブコマンド群。"""

import json
import sys
from typing import Any

import typer

from cli._io import _print_json
from core.discovery import discover_systems

runs_app = typer.Typer(no_args_is_help=True, help="verification run history")
analysis_app = typer.Typer(no_args_is_help=True, help="@analysis 関数の実行")


def _bootstrap() -> None:
    discover_systems()


# ─── runs ────────────────────────────────────────────────────────────


@runs_app.command("list")
def runs_list(limit: int = typer.Option(20, "--limit", "-n", min=0, help="最大件数")) -> None:
    """verification run 一覧を新しい順に表示。"""
    from core.persistence.runs import list_runs, run_to_dict

    _print_json({"runs": [run_to_dict(run) for run in list_runs(limit=limit)]})


@runs_app.command("show")
def runs_show(run_id: str) -> None:
    """単一 verification run の詳細を表示。"""
    from core.persistence.runs import get_run, run_to_dict

    run = get_run(run_id)
    if run is None:
        typer.echo(f"Error: run '{run_id}' not found", err=True)
        raise typer.Exit(code=1)
    _print_json(run_to_dict(run))


@runs_app.command("latest")
def runs_latest() -> None:
    """最新 verification run を表示。"""
    from core.persistence.runs import get_run, latest_run_id, run_to_dict

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
    from core.persistence.runs import get_run_artifact

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
    from core.surface_ops.introspection import list_analyses_summary

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

    from core.analysis.runner import AnalysisArgumentError, AnalysisNotFound
    from core.analysis.runner import run_analysis as _run_analysis

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
