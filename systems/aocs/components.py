"""aocs system components."""

from schema import Component, fld


class SunSenser(Component):
    """太陽センサ。複数個搭載することが多いので MultiInstance。"""

    fov_deg: float = fld(ge=0, le=180, desc="視野角")

    class Design:
        pass
