import datetime
from typing import Any

from saim.shared.verify.types import check_type


def pa_int(to_ch: Any, /) -> int:
    return check_type(to_ch, int, -1)


def pa_float(to_ch: Any, /) -> float:
    return check_type(to_ch, float, -1.0)


def pa_opt_int(to_ch: Any, /) -> int | None:
    return check_type(to_ch, int, None)


def pa_opt_float(to_ch: Any, /) -> float | None:
    return check_type(to_ch, float, None)


def pa_str(to_ch: Any, /) -> str:
    return check_type(to_ch, str, "")


def pa_opt_str(to_ch: Any, /) -> str | None:
    return check_type(to_ch, str, None)


def pa_opt_date(to_ch: Any, /) -> datetime.date | None:
    return check_type(to_ch, datetime.date, None)


def pa_date(to_ch: Any, /) -> datetime.date:
    return check_type(to_ch, datetime.date, datetime.date.today())


def pa_int_bool(to_ch: Any, /) -> bool:
    return check_type(to_ch, int, -1) == 1
