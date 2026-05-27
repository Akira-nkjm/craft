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

import typer

from craft.cli.commands.data import merge_cmd, scaffold_cmd, verify_cmd
from craft.cli.commands.instances import create_cmd, delete_cmd, patch_cmd, put_cmd, spec_app
from craft.cli.commands.maintenance import diff_cmd, gen_stubs_cmd, history_cmd, init_app
from craft.cli.commands.runs_analysis import analysis_app, runs_app
from craft.cli.commands.schema import get, schema_app
from craft.core.discovery import discover_systems

# Typer サブアプリ
app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Craft — Concept Registry for Automated spacecraFT design",
)
app.add_typer(schema_app, name="schema")
app.command("get")(get)
app.add_typer(analysis_app, name="analysis")
app.add_typer(init_app, name="init")
app.add_typer(spec_app, name="spec")
app.add_typer(runs_app, name="runs")

# Top-level commands from split modules
app.command("create")(create_cmd)
app.command("put")(put_cmd)
app.command("patch")(patch_cmd)
app.command("delete")(delete_cmd)
app.command("merge")(merge_cmd)
app.command("scaffold")(scaffold_cmd)
app.command("verify")(verify_cmd)
app.command("history")(history_cmd)
app.command("diff")(diff_cmd)
app.command("gen-stubs")(gen_stubs_cmd)


def _bootstrap() -> None:
    discover_systems()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
