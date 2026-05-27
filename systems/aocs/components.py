"""aocs system components."""

from craft.schema import Component, Placeable, fld


class SunSenser(Component, Placeable):
    """太陽センサ。複数個搭載することが多いので MultiInstance。"""

    fov_deg: float = fld(ge=0, le=180, desc="視野角")

    class Design:
        pass
