"""@analysis decorator.

`@analysis(verify=False)` で計算関数を registry に登録、`scope.py` 側で
veriq Scope に貼り直す。`verify=True` なら veriq.verification として登録される。
"""

from collections.abc import Callable, Iterable
from typing import Any

from craft.schema._subclass_helpers import infer_system_from_caller
from craft.schema.registry import AnalysisDefinition, SourceLocation, default_registry

_UNSET = object()


def analysis(
    _func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    system: str | None | object = _UNSET,
    verify: bool = False,
    imports: Iterable[str] = (),
    cache: bool = False,
    desc: str | None = None,
) -> Any:
    """Analysis 関数を登録する decorator。

    Args:
        name: registry 上の名前（default は関数名）。
        system: 明示する場合は文字列、ad-hoc にしたい場合は `None` を明示で渡す。
            未指定の場合はファイルパスから自動推論。
        verify: True なら verification（戻り値は bool or vq.Table[K, bool]）。
        imports: cross-scope import するスコープ名のリスト。
        cache: 結果をキャッシュするか（現状はメタ情報のみ）。
        desc: 説明。
    """

    def wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        analysis_name = name or func.__name__
        if system is _UNSET:
            inferred: str | None = infer_system_from_caller()
        else:
            inferred = system  # type: ignore[assignment]

        # 下位 decorator（e.g. @auto_inject_refs）が必要な scope を提示していれば
        # `imports=` 未指定時はそれを採用する。
        effective_imports = (
            tuple(imports) if imports else tuple(getattr(func, "__craft_imports__", ()))
        )

        default_registry.register_analysis(
            AnalysisDefinition(
                name=analysis_name,
                system=inferred,
                func=func,
                verify=verify,
                imports=effective_imports,
                cache=cache,
                source=SourceLocation.of(func),
                desc=desc or func.__doc__,
            )
        )
        return func

    if _func is not None:
        return wrap(_func)
    return wrap
