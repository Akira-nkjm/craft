"""ユーザー定義の共通 enum・型。"""

from enum import StrEnum


class OperationMode(StrEnum):
    """衛星の運用モード。値はここで自由に追加・変更できる。"""

    SAFE = "safe"
    NOMINAL = "nominal"
    SCIENCE = "science"
    SAFE_HOLD = "safe_hold"
