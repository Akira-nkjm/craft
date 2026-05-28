"""AOCS fixture components."""

from craft.schema import Component, Placeable, fld


class SunSenser(Component, Placeable):
    """Pre-SEIRIOS singleton sun sensor fixture."""

    fov_deg: float = fld(ge=0, le=180, desc="視野角")

    class Design:
        pass
