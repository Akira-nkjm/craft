"""scope-input 経路が merge 経路と同一結果を返すことを保証する。

veriq の `Scope(input=...)` を使う `evaluate_project_via_scope_input` は、
`generated/merged.toml` を介さずに各 `systems/<name>/data.toml` を直接ロードする。
既存の merge 経路（`evaluate_project_from_merged`）と計算・検証結果が一致することを
確認し、merge 置き換えの安全性を担保する。
"""

from craft.core.pipeline.veriq_project import (
    evaluate_project_from_merged,
    evaluate_project_via_scope_input,
)


def test_scope_input_matches_merge(clean_generated_dir):
    """両経路の leaf 値・success が完全一致する。"""
    _, res_merge = evaluate_project_from_merged()
    _, res_scope = evaluate_project_via_scope_input()

    assert res_merge.success == res_scope.success

    merge_leaves = dict(res_merge.iter_leaf_values())
    scope_leaves = dict(res_scope.iter_leaf_values())

    assert scope_leaves  # 何かしら評価されている
    assert scope_leaves == merge_leaves


def test_scope_input_skips_merge_artifacts(clean_generated_dir):
    """scope-input 経路は merged.toml を生成しない。"""
    evaluate_project_via_scope_input()
    assert not (clean_generated_dir / "merged.toml").exists()
