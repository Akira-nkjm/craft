"""共通の enum・型。"""

from enum import StrEnum


class OperationMode(StrEnum):
    """衛星の運用モード。"""

    SAFE = "safe"
    NOMINAL = "nominal"
    SCIENCE = "science"
    SAFE_HOLD = "safe_hold"
