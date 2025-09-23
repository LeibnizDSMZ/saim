import re
import warnings
from collections.abc import Callable
from typing import Any, Final
import datetime


def check_str_warn(
    to_check: str,
    checker: Callable[[str], bool],
    warn: str,
    warn_type: type[UserWarning],
    /,
) -> str:
    if checker(to_check):
        return to_check
    warnings.warn(warn, warn_type, stacklevel=2)
    return ""


def check_type[T](to_check: Any, typ: type[T], default: T, /) -> T:
    if isinstance(to_check, typ):
        return to_check
    return default


def check_type_strict[T](to_check: Any, typ: type[T], /) -> T:
    if isinstance(to_check, typ):
        return to_check
    raise ValueError(f"invalid type - {to_check}")


def check_bool_int(to_check: Any, truth: int, default: bool, /) -> bool:
    if isinstance(to_check, int):
        return to_check == truth
    return default


def check_value_or[U](
    to_check: Any, checkers: list[Callable[[Any], bool]], parse: Callable[[Any], U], /
) -> U:
    for check in checkers:
        if check(to_check):
            return parse(to_check)
    raise ValueError(f"invalid type check - {to_check}")


def ch_int(to_ch: Any, /) -> bool:
    return isinstance(to_ch, int)


def ch_opt_int(to_ch: Any, /) -> bool:
    return to_ch is None or isinstance(to_ch, int)


def ch_float(to_ch: Any, /) -> bool:
    return isinstance(to_ch, float)


def ch_opt_float(to_ch: Any, /) -> bool:
    return to_ch is None or isinstance(to_ch, float)


def ch_f_str(to_ch: Any, /) -> bool:
    return isinstance(to_ch, str) and to_ch != ""


def ch_str(to_ch: Any, /) -> bool:
    return isinstance(to_ch, str)


def ch_opt_str(to_ch: Any, /) -> bool:
    return to_ch is None or isinstance(to_ch, str)


def ch_date(to_ch: Any, /) -> bool:
    return isinstance(to_ch, datetime.date)


def ch_opt_date(to_ch: Any, /) -> bool:
    return to_ch is None or isinstance(to_ch, datetime.date)


_PATTERN_FLOAT: Final[str] = r"^\s*[-+]?(\d+(?:\.\d+))?\s*$"
_FLOAT_RE: Final[re.Pattern[str]] = re.compile(_PATTERN_FLOAT)


def ch_str_float(num: str, lim: float, msg: str, /) -> None:
    mat = _FLOAT_RE.match(num)
    if mat is None or not isinstance(mat.group(1), str) or float(num) > lim:
        raise ValueError(f"{msg} malformed - {num}")
