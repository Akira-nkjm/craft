import marimo

__generated_with = "0.23.9"
app = marimo.App()


@app.cell
def _():
    import sys
    from pathlib import Path

    import marimo as mo

    nb_dir = Path(mo.notebook_dir() or Path.cwd())
    if (
        not (nb_dir / "satellite_scene.py").is_file()
        and (nb_dir / "scripts" / "satellite_scene.py").is_file()
    ):
        nb_dir = nb_dir / "scripts"
    if str(nb_dir) not in sys.path:
        sys.path.insert(0, str(nb_dir))

    # pyrefly: ignore[missing-import]  # 実行時に sys.path へ scripts/ を追加して解決
    from satellite_scene import build_figure, build_scene

    return build_figure, build_scene, mo, nb_dir


@app.cell
def _(build_scene, nb_dir):
    placements, envelope = build_scene(nb_dir.parent / "systems")
    systems = sorted({record.system for record in placements})
    return envelope, placements, systems


@app.cell
def _(mo, systems):
    system_filter = mo.ui.multiselect(options=systems, value=systems, label="system")
    show_envelope = mo.ui.switch(True, label="エンベロープ表示")
    translucent_large = mo.ui.switch(True, label="大箱を半透明")
    mo.vstack([system_filter, mo.hstack([show_envelope, translucent_large])])
    return show_envelope, system_filter, translucent_large


@app.cell
def _(mo, placements, system_filter):
    from collections import Counter

    selected_systems = set(system_filter.value)
    visible = [record for record in placements if record.system in selected_systems]
    total_counts = Counter(record.system for record in placements)
    visible_counts = Counter(record.system for record in visible)
    lines = [
        f"- {system}: {visible_counts.get(system, 0)} / {total_counts[system]}"
        for system in sorted(total_counts)
    ]
    mo.md(
        "### Placement count\n\n"
        f"total: **{len(placements)}** / visible: **{len(visible)}**\n\n" + "\n".join(lines)
    )
    return selected_systems


@app.cell
def _(build_figure, envelope, placements, selected_systems, show_envelope, translucent_large):
    fig = build_figure(
        placements,
        envelope,
        systems=selected_systems,
        show_envelope=show_envelope.value,
        translucent_large=translucent_large.value,
    )
    return (fig,)


@app.cell
def _(fig, mo):
    mo.ui.plotly(fig, config={"displaylogo": False, "responsive": True})
    return


if __name__ == "__main__":
    app.run()
