"""TOML 共通整形ロジック (merge / scaffold 両方が使う)。

仕様: plan/Craft/01_仕様/データパイプライン.md §4.6

整形ルール:
- field 順序: registry の宣言順（class 本体 → trait 由来 → Design → Requirements → meta）
- コメント: `# <desc> [unit]` を field 直後に付ける
- `# TODO:` マーカー: 必須 field で default 無しのものに付ける
- 数値: float は `1.0` 形式（明示的に小数点）
"""

from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo, PydanticUndefined
from tomlkit import TOMLDocument
from tomlkit.items import Table


def format_field_comment(finfo: FieldInfo) -> str | None:
    """`# <desc> [unit]` 形式のコメント文字列を返す（不要なら None）。"""
    extra = finfo.json_schema_extra if isinstance(finfo.json_schema_extra, dict) else {}
    unit = extra.get("unit") if extra else None
    desc = finfo.description
    parts: list[str] = []
    if desc:
        parts.append(str(desc))
    if unit:
        parts.append(f"[{unit}]")
    if not parts:
        return None
    return " ".join(parts)


def is_required(finfo: FieldInfo) -> bool:
    """default も default_factory も無いなら required。"""
    return finfo.default is PydanticUndefined and finfo.default_factory is None


def todo_marker(finfo: FieldInfo) -> str | None:
    """`# TODO: required, ge=0` 風の TODO 文字列。"""
    if not is_required(finfo):
        return None
    constraints: list[str] = []
    md = finfo.metadata or []
    for m in md:
        for attr in ("ge", "le", "gt", "lt"):
            v = getattr(m, attr, None)
            if v is not None:
                constraints.append(f"{attr}={v}")
    base = "TODO: required"
    if constraints:
        base += " " + " ".join(constraints)
    return base


def apply_field_comments(table: Table, model: type[BaseModel]) -> None:
    """既存の Table に対し、registry の field comment を付与。

    Pydantic model の `model_fields` を順序ベースで走査。
    """
    for fname, finfo in model.model_fields.items():
        if fname not in table:
            continue
        comment = format_field_comment(finfo)
        if comment:
            with _suppress_errors():
                table[fname].comment(comment)


def write_with_comments(doc: TOMLDocument, target_path: Any) -> None:
    """`tomlkit.dumps` でファイル書き出し。`core.toml_io.write_toml_atomic`
    と用途が被るが、こちらは「formatter が組んだ doc」専用。"""
    from core.toml_io import write_toml_atomic

    write_toml_atomic(target_path, doc)


# ─── helpers ──────────────────────────────────────────────────────────


class _suppress_errors:  # noqa: N801 — context manager 用、private util
    """tomlkit の item に comment を付けるとき、scalar item が対応しない場合がある。"""

    def __enter__(self) -> _suppress_errors:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return exc_type is not None and issubclass(exc_type, (AttributeError, KeyError, TypeError))


def order_fields_by_registry(table: Table, model: type[BaseModel]) -> None:
    """既存 Table の field 順序を model.model_fields の順に並び替え。

    キーを削除後に残る non-keyed body アイテム（セクション区切りコメント・
    空白行）も除去する。放置すると再追加したフィールドが末尾に押し出される。
    """
    desired = list(model.model_fields.keys())
    items_in_order: list[tuple[str, Any]] = []
    extras: list[tuple[str, Any]] = []
    for fname in desired:
        if fname in table:
            items_in_order.append((fname, table[fname]))
    for fname in list(table.keys()):
        if fname not in desired:
            extras.append((fname, table[fname]))
    # 全 key を削除
    for fname in list(table.keys()):
        del table[fname]
    # 削除後に残る non-keyed アイテム（コメント・空白）も除去して順序を確定させる
    table.value._body[:] = [(k, v) for k, v in table.value._body if k is not None]
    for fname, val in items_in_order:
        table[fname] = val
    for fname, val in extras:
        table[fname] = val


def is_float_field(finfo: FieldInfo) -> bool:
    """field 型が float (またはその union) ならば True。"""
    annotation = finfo.annotation
    if annotation is float:
        return True
    args = getattr(annotation, "__args__", ())
    return float in args


def normalize_float_values(table: Table, model: type[BaseModel]) -> None:
    """float field の値が int で書かれていたら float に変換。"""
    for fname, finfo in model.model_fields.items():
        if fname not in table:
            continue
        if not is_float_field(finfo):
            continue
        val = table[fname]
        try:
            current = val.value if hasattr(val, "value") else val
        except AttributeError, TypeError:
            current = val
        if isinstance(current, int) and not isinstance(current, bool):
            with _suppress_errors():
                table[fname] = float(current)


def format_section(table: Table, model: type[BaseModel]) -> None:
    """`order → comments → float 正規化` を 1 セクションに適用。"""
    order_fields_by_registry(table, model)
    apply_field_comments(table, model)
    normalize_float_values(table, model)


def default_value(finfo: FieldInfo) -> Any:
    """field の TOML 用 default 値。None は呼び元で skip。"""
    if finfo.default is not PydanticUndefined and finfo.default is not Ellipsis:
        return finfo.default
    if finfo.default_factory is not None:
        try:
            return finfo.default_factory()  # type: ignore[call-arg]
        except Exception:
            pass
    return _placeholder_for_type(finfo.annotation)


def _placeholder_for_type(annotation: Any) -> Any:
    from typing import Literal

    origin = getattr(annotation, "__origin__", None)

    # Literal → 最初の値をそのまま返す
    if origin is Literal:
        args = getattr(annotation, "__args__", None)
        if args:
            return args[0]

    bare = origin or annotation
    if bare is float:
        return 0.0
    if bare is int:
        return 0
    if bare is bool:
        return False
    if bare is str:
        return ""
    if bare in (list, tuple, set):
        return []
    if bare is dict:
        return {}
    return ""
