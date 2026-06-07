import marimo

__generated_with = "0.23.9"
app = marimo.App(width="full")


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
    from placement_edit import write_placement

    # pyrefly: ignore[missing-import]
    from satellite_scene import build_figure, build_scene

    return build_figure, build_scene, mo, nb_dir, write_placement


@app.cell
def _(mo):
    # 保存後にファイルを再読み込みするためのトリガ
    reload_button = mo.ui.run_button(label="🔄 ファイル再読み込み")
    reload_button  # noqa: B018 — marimo セルの表示式
    return (reload_button,)


@app.cell
def _(build_scene, nb_dir, reload_button):
    reload_button  # noqa: B018 — 依存させて保存後の再読み込みを可能にする
    placements, envelope = build_scene(nb_dir.parent / "systems")
    systems = sorted({record.system for record in placements})
    # 表示ラベル → record の対応（編集対象の選択に使う）
    record_by_label = {f"{r.system} / {r.name}": r for r in placements}
    return envelope, placements, record_by_label, systems


@app.cell
def _(mo, systems):
    system_filter = mo.ui.multiselect(options=systems, value=systems, label="system")
    show_envelope = mo.ui.switch(True, label="エンベロープ表示")
    translucent_large = mo.ui.switch(True, label="大箱を半透明")
    mo.vstack([system_filter, mo.hstack([show_envelope, translucent_large])])
    return show_envelope, system_filter, translucent_large


@app.cell
def _(mo, record_by_label):
    # 編集するコンポーネントを選ぶ
    labels = sorted(record_by_label)
    component_selector = mo.ui.dropdown(
        options=labels, value=labels[0], label="編集するコンポーネント"
    )
    component_selector  # noqa: B018 — marimo セルの表示式
    return (component_selector,)


@app.cell
def _(component_selector, mo, record_by_label):
    # 選択中 record の現在値で編集 UI を初期化（選択が変わると再生成される）
    # pyrefly: ignore[missing-import]
    from placement_edit import EDITABLE_FACES, EDITABLE_SIDES

    selected = record_by_label[component_selector.value]
    face_input = mo.ui.dropdown(options=list(EDITABLE_FACES), value=selected.face, label="face")
    side_input = mo.ui.dropdown(options=list(EDITABLE_SIDES), value=selected.side, label="side")
    u_input = mo.ui.number(value=float(selected.u), step=1.0, label="u [mm]")
    v_input = mo.ui.number(value=float(selected.v), step=1.0, label="v [mm]")
    w_input = mo.ui.number(value=float(selected.w), start=0.0, step=1.0, label="w [mm]")
    rz_input = mo.ui.number(value=float(selected.rz), step=5.0, label="rz [deg]")
    dx_input = mo.ui.number(value=float(selected.size[0]), start=0.0, step=1.0, label="dx [mm]")
    dy_input = mo.ui.number(value=float(selected.size[1]), start=0.0, step=1.0, label="dy [mm]")
    dz_input = mo.ui.number(value=float(selected.size[2]), start=0.0, step=1.0, label="dz [mm]")
    save_button = mo.ui.run_button(label="💾 data.toml に保存")

    mo.vstack(
        [
            mo.md(f"**{component_selector.value}**"),
            mo.md("u/v: 機体中心からの符号付きオフセット [mm], w: 取付面からの距離 [mm]"),
            mo.hstack([face_input, side_input], justify="start"),
            mo.md("位置 (u/v/w/rz)"),
            mo.hstack([u_input, v_input, w_input, rz_input], justify="start"),
            mo.md("サイズ (bounding box dx/dy/dz)"),
            mo.hstack([dx_input, dy_input, dz_input], justify="start"),
            save_button,
        ]
    )
    return (
        dx_input,
        dy_input,
        dz_input,
        face_input,
        rz_input,
        save_button,
        selected,
        side_input,
        u_input,
        v_input,
        w_input,
    )


@app.cell
def _(
    dx_input,
    dy_input,
    dz_input,
    face_input,
    placements,
    rz_input,
    selected,
    side_input,
    u_input,
    v_input,
    w_input,
):
    import dataclasses

    # 編集値で選択 record を差し替えた一覧（図にライブ反映）
    edited_record = dataclasses.replace(
        selected,
        face=face_input.value,
        side=side_input.value,
        u=float(u_input.value),
        v=float(v_input.value),
        w=float(w_input.value),
        rz=float(rz_input.value),
        size=(float(dx_input.value), float(dy_input.value), float(dz_input.value)),
    )
    edited_placements = [edited_record if r is selected else r for r in placements]
    return (edited_placements,)


@app.cell
def _(edited_placements, mo, system_filter):
    from collections import Counter

    selected_systems = set(system_filter.value)
    visible = [r for r in edited_placements if r.system in selected_systems]
    total_counts = Counter(r.system for r in edited_placements)
    visible_counts = Counter(r.system for r in visible)
    lines = [
        f"- {system}: {visible_counts.get(system, 0)} / {total_counts[system]}"
        for system in sorted(total_counts)
    ]
    mo.md(
        "### Placement count\n\n"
        f"total: **{len(edited_placements)}** / visible: **{len(visible)}**\n\n" + "\n".join(lines)
    )
    return (selected_systems,)


@app.cell
def _(
    build_figure,
    edited_placements,
    envelope,
    selected_systems,
    show_envelope,
    translucent_large,
):
    fig = build_figure(
        edited_placements,
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


@app.cell
def _(
    dx_input,
    dy_input,
    dz_input,
    face_input,
    mo,
    nb_dir,
    rz_input,
    save_button,
    selected,
    side_input,
    u_input,
    v_input,
    w_input,
    write_placement,
):
    # 「保存」クリック時のみ data.toml へ書き戻し（コメント保持）
    if save_button.value:
        saved_path = write_placement(
            nb_dir.parent / "systems",
            selected.system,
            selected.path,
            face=face_input.value,
            side=side_input.value,
            u=float(u_input.value),
            v=float(v_input.value),
            w=float(w_input.value),
            rz=float(rz_input.value),
            dx=float(dx_input.value),
            dy=float(dy_input.value),
            dz=float(dz_input.value),
        )
        status = mo.md(
            f"✅ 保存しました: `{saved_path}` "
            f"({selected.name}: face={face_input.value} side={side_input.value} "
            f"u={u_input.value} v={v_input.value} w={w_input.value} "
            f"size=({dx_input.value},{dy_input.value},{dz_input.value}))\n\n"
            "→ 上の **🔄 ファイル再読み込み** で反映を確認できます。"
        )
    else:
        status = mo.md("_編集後 **💾 保存** で `data.toml` に書き戻します。_")
    status  # noqa: B018 — marimo セルの表示式
    return


if __name__ == "__main__":
    app.run()
