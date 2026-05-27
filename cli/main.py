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

from core.discovery import discover_systems

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


def _bootstrap() -> None:
    discover_systems()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
