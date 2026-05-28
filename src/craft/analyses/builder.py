"""Analysis parameter injection helpers.

`systems/<sys>/analyses.py` で 30+ 個の Annotated 引数を手書きする代わりに、
decorator で registry を query して**シグネチャを動的注入**する。
登録自体は通常通り `@analysis` が行う。

使用例（systems/power/analyses.py）::

    @analysis(desc="モード別 全バス消費電力")
    @auto_inject_refs(
        trait="PowerConsuming",
        extra_refs=[("mission", "operation_mode_configs")],
    )
    def bus_power_per_mode_w(mode_configs, *tables) -> dict[str, float]:
        return power_per_mode(mode_configs, *tables)

`@auto_inject_refs` が PowerConsuming コンポを registry から全列挙し、
`Annotated[vq.Table, vq.Ref(...)]` 付きラッパを生成する。`@analysis` は
そのラッパの shema を受け取り、必要な `imports` も `__craft_imports__`
属性から自動で吸収する。
"""

from collections.abc import Callable, Sequence
from typing import Annotated, Any

import veriq as vq

from craft.schema._subclass_helpers import infer_system_from_caller
from craft.schema.registry import default_registry


def all_component_refs(
    *,
    trait: str | None = None,
    traits_all: Sequence[str] = (),
    traits_any: Sequence[str] = (),
) -> list[tuple[str, str]]:
    """registry の全 component を ``(scope, ref_name)`` ペアで返す。

    ``ref_name`` は cardinality に応じて切り替わる:
      - MultiInstance: ``plural``（例: ``batteries``）
      - Singleton: ``name``（例: ``obc``）

    Args:
        trait: 単一 trait での AND filter。``traits_all`` への shortcut。
        traits_all: 指定した trait を **全て** 持つ component のみ返す（AND）。
        traits_any: 指定した trait の **いずれか** を持つ component のみ返す（OR）。
            ``traits_all`` と併用すると AND(all) かつ ANY(any) になる。
    """
    required: list[str] = list(traits_all)
    if trait:
        required.append(trait)

    defs = default_registry.components()
    if required:
        defs = [d for d in defs if all(t in d.traits for t in required)]
    if traits_any:
        any_set = set(traits_any)
        defs = [d for d in defs if any_set.intersection(d.traits)]
    return [(d.system, d.plural if d.cardinality == "multi" else d.name) for d in defs]


def auto_inject_refs(
    *,
    trait: str | None = None,
    traits_all: Sequence[str] = (),
    traits_any: Sequence[str] = (),
    extra_refs: Sequence[tuple[str, str]] = (),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """対象関数のシグネチャに `Annotated[vq.Table, vq.Ref(...)]` 引数を一括注入する decorator。

    `@analysis` の **直下**（`@auto_inject_refs` が下、`@analysis` が上）に置く。
    内部では registry を query して引数列を生成し、元関数を call back する
    ラッパ関数を返す。 必要な `imports` リストはラッパ関数の `__craft_imports__`
    属性に格納され、`@analysis` 側がそれを読む。

    Args:
        trait: 単一 trait での AND filter（``traits_all=[trait]`` と同じ）。
        traits_all: 指定 trait を**全て**持つ component のみ（AND）。
            例: ``["PowerConsuming", "TemperatureSensitive"]`` → 両方を持つもの。
        traits_any: 指定 trait の**いずれか**を持つ component のみ（OR）。
            ``traits_all`` と併用可能（AND × OR）。
        extra_refs: 追加の ``(scope, ref_name)`` ペア。**先頭**に並ぶ。

    元関数は ``(*tables)`` または ``(extra1, ..., *tables)`` の位置引数で受け取る。
    生成ラッパは extra_refs → component_refs の順に渡す。
    """

    def decorator(user_func: Callable[..., Any]) -> Callable[..., Any]:
        caller_system = infer_system_from_caller()
        component_refs = all_component_refs(
            trait=trait,
            traits_all=traits_all,
            traits_any=traits_any,
        )
        all_refs: list[tuple[str, str]] = list(extra_refs) + component_refs

        imports = tuple(sorted({s for s, _ in all_refs if s != caller_system}))

        # 戻り値型を user_func の annotation から拾う
        ret_anno = user_func.__annotations__.get("return", "float")
        ret_str = _render_return_annotation(ret_anno)

        param_lines: list[str] = []
        arg_names: list[str] = []
        for scope, ref_name in all_refs:
            scope_kw = "" if scope == caller_system else f", scope='{scope}'"
            param_lines.append(
                f"    {ref_name}: Annotated[vq.Table, vq.Ref('$.{ref_name}'{scope_kw})]",
            )
            arg_names.append(ref_name)

        args_src = ",\n".join(param_lines)
        args_call = ", ".join(arg_names)

        src = (
            f"def {user_func.__name__}(\n"
            f"{args_src},\n"
            f") -> {ret_str}:\n"
            f"    return _user({args_call})\n"
        )

        namespace: dict[str, Any] = {
            "Annotated": Annotated,
            "vq": vq,
            "_user": user_func,
            "dict": dict,
            "list": list,
            "float": float,
            "int": int,
            "str": str,
            "bool": bool,
        }
        exec(src, namespace)  # noqa: S102 — local trusted source generation
        wrapper = namespace[user_func.__name__]
        wrapper.__doc__ = user_func.__doc__
        wrapper.__craft_imports__ = imports
        return wrapper

    return decorator


def _render_return_annotation(annotation: Any) -> str:
    """``float`` → ``"float"`` / ``dict[str, float]`` → そのままの文字列。"""
    if isinstance(annotation, str):
        return annotation
    name = getattr(annotation, "__name__", None)
    if name:
        return name
    return repr(annotation)
