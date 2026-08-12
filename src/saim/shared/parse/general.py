import datetime
from typing import Any

from saim.shared.parse.types import ch_type


def pa_int(to_ch: Any, /) -> int:
    return ch_type(to_ch, int, -1)


def pa_float(to_ch: Any, /) -> float:
    return ch_type(to_ch, float, -1.0)


def pa_opt_int(to_ch: Any, /) -> int | None:
    return ch_type(to_ch, int, None)


def pa_opt_float(to_ch: Any, /) -> float | None:
    return ch_type(to_ch, float, None)


def pa_str(to_ch: Any, /) -> str:
    return ch_type(to_ch, str, "")


def pa_opt_str(to_ch: Any, /) -> str | None:
    return ch_type(to_ch, str, None)


def pa_opt_date(to_ch: Any, /) -> datetime.date | None:
    return ch_type(to_ch, datetime.date, None)


def pa_date(to_ch: Any, /) -> datetime.date:
    return ch_type(to_ch, datetime.date, datetime.date.today())


def pa_int_bool(to_ch: Any, /) -> bool:
    return ch_type(to_ch, int, -1) == 1
