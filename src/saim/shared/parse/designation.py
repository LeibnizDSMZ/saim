from typing import Any


def strip_designation(des: Any) -> Any:
    if isinstance(des, str) and len(des) > 61:
        return des[:61] + "..."
    return des
