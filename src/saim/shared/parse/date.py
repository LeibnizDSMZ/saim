from dataclasses import dataclass
import re
from datetime import date, datetime
from re import Pattern
from typing import Any, Final, TypeGuard, final

from dateutil import parser
from dateutil.parser import ParserError


# for year >= 1000
_YEAR_RANGE: Final[str] = r"(\d{4})-(?:\d{4})"
_YEAR: Final[str] = r"(\d{4})"
# YEAR must be 4 digits to decrease inconsistencies in date
_FULL_DATE: Final[str] = r"(\d{4})[\-./](\d{1,2})(?:[\-./](\d{1,2}))?"
_FULL_DATE_REV: Final[str] = r"(?:(\d{1,2})[\-./])?(\d{1,2})[\-./](\d{4})"

_DOR: Final[str] = r"|".join((_YEAR_RANGE, _FULL_DATE, _FULL_DATE_REV, _YEAR))

_REV_DATE_P: Final[Pattern[str]] = re.compile(rf"^{_FULL_DATE_REV}")
_DATE_P: Final[Pattern[str]] = re.compile(rf"^{_FULL_DATE}")
_YEAR_P: Final[Pattern[str]] = re.compile(rf"^{_YEAR}")
_YEAR_RANGE_P: Final[Pattern[str]] = re.compile(rf"^{_YEAR_RANGE}")
_FULL_DATE_P: Final[Pattern[str]] = re.compile(r"^\D*(" + _DOR + r").*$")

_GET_YEAR: Final[Pattern[str]] = re.compile(_YEAR)
_EARLIEST_YEAR: Final[int] = 1800

_RKMS: Final[str] = r"^\/?\d{4}(?:-\d{2}){0,2}(?:\/|\/\d{4}(?:-\d{2}){0,2})?$"
_RKMS_SL: Final[str] = r"^[^\/]*\/?[^\/]*$"

_RKMS_REG: Final[tuple[Pattern[str], ...]] = (re.compile(_RKMS), re.compile(_RKMS_SL))


def get_rkms_regex() -> tuple[Pattern[str], ...]:
    return _RKMS_REG


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class CompleteDate:
    date: datetime
    month: bool = False
    day: bool = False

    def to_string(self, full: bool, /) -> str:
        out = f"{self.date.year}"
        month = full and self.month
        if month:
            out += f"-{_add_zero(self.date.month)}"
        if month and self.day:
            out += f"-{_add_zero(self.date.day)}"
        return out


def _extract_date(pos_date: str, cur_year: int, /) -> str | None:
    if (
        (date := _FULL_DATE_P.match(pos_date)) is not None
        and (year := _GET_YEAR.search(par_date := str(date.group(1)))) is not None
        and _is_reasonable_date(pos_date, int(year.group(1)), cur_year)
    ):
        return par_date
    return None


def _cur_year_in_str(date: str, ext_year: int, cur_year: int, /) -> bool:
    if ext_year != cur_year:
        return True
    return f"{cur_year!s}" in date


def _is_reasonable_date(date: str, ext_year: int, cur_year: int, /) -> bool:
    return _EARLIEST_YEAR <= ext_year <= cur_year and _cur_year_in_str(
        date, ext_year, cur_year
    )


def _str_int_strict(to_parse: Any, /) -> int:
    if isinstance(to_parse, str):
        return int(to_parse)
    raise TypeError(f"{to_parse} is not an integer")


def _str_int(to_parse: Any, /) -> int | None:
    try:
        if isinstance(to_parse, str):
            return int(to_parse)
    except Exception:
        return None
    return None


def _cor_mon_day(num: int | None, lim: int) -> TypeGuard[int]:
    if num is None:
        return False
    return 1 <= num <= lim


def _create_full_datetime(*date: Any) -> CompleteDate | None:
    year, month, day = date
    year_f = _str_int_strict(year)
    month_f = _str_int(month)
    day_f = _str_int(day)
    if _cor_mon_day(month_f, 12) and _cor_mon_day(day_f, 31):
        try:
            return CompleteDate(
                date=datetime(year=year_f, month=month_f, day=day_f), month=True, day=True
            )
        except ValueError:
            pass
    if _cor_mon_day(month_f, 12):
        return CompleteDate(date=datetime(year=year_f, month=month_f, day=1), month=True)
    return CompleteDate(date=datetime(year=year_f, month=1, day=1))


def _create_date_time(date: str, /) -> CompleteDate | None:
    cda = date.strip()
    if (ex_dat := _YEAR_RANGE_P.match(cda)) is not None:
        return CompleteDate(date=datetime(_str_int_strict(ex_dat.group(1)), 1, 1))
    if (ex_dat := _DATE_P.match(cda)) is not None:
        return _create_full_datetime(ex_dat.group(1), ex_dat.group(2), ex_dat.group(3))
    if (ex_dat := _REV_DATE_P.match(cda)) is not None:
        return _create_full_datetime(ex_dat.group(3), ex_dat.group(2), ex_dat.group(1))
    if (ex_dat := _YEAR_P.match(cda)) is not None:
        return CompleteDate(date=datetime(_str_int_strict(ex_dat.group(1)), 1, 1))
    return None


def get_date(pos_date: str, /) -> CompleteDate | None:
    cur_year = datetime.now().year
    date = _extract_date(pos_date, cur_year)
    if date is not None and (ext_date := _create_date_time(date)) is not None:
        return ext_date
    try:
        parsed_date = parser.parse(pos_date, fuzzy=False)
        if _is_reasonable_date(pos_date, parsed_date.year, cur_year):
            return CompleteDate(date=parsed_date)
    except (ParserError, OverflowError):
        return None
    return None


def is_reasonable_date(pos_date: str, /) -> bool:
    if len(pos_date) < 4:
        return False
    return get_date(pos_date) is not None


def check_date_str(dat: str | datetime | date, /) -> str:
    if isinstance(dat, (datetime, date)):
        return date_to_str(dat, True)
    if not is_reasonable_date(dat):
        raise ValueError(f"{dat} is possible malformed, expected a date format")
    return dat


def _add_zero(value: int, /) -> str:
    if value < 10:
        return f"0{value!s}"
    return f"{value!s}"


def date_to_str(
    date_el: date | datetime | CompleteDate | None, full: bool = False, /
) -> str:
    if date_el is None:
        return ""
    if full and isinstance(date_el, (datetime, date)):
        return f"{date_el.year}-{_add_zero(date_el.month)}-{_add_zero(date_el.day)}"
    if isinstance(date_el, CompleteDate):
        return date_el.to_string(full)
    return f"{date_el.year}"


def get_date_or_rkms(date: str, /) -> str:
    for reg in _RKMS_REG:
        if reg.match(date) is None:
            if (p_dat := get_date(date)) is not None:
                return date_to_str(p_dat, True)
            return ""
    return date


def date_to_year(date_el: CompleteDate | datetime | date | None, /) -> int | None:
    if date_el is None:
        return None
    if isinstance(date_el, CompleteDate):
        return date_el.date.year
    return date_el.year


def get_date_year(date: str, /) -> int:
    if not is_reasonable_date(date):
        return -1
    parsed_date = date_to_year(get_date(date))
    if parsed_date is None:
        return -1
    return parsed_date


def year_to_str(year: int | None, full: bool = False, /) -> str | None:
    if year is None or year < 1000:
        return None
    if full:
        return f"{year}-01-01"
    return str(year)


def check_rkms(date: str, /) -> str:
    for reg in get_rkms_regex():
        if reg.match(date) is None:
            raise ValueError(f"wrong rkms date format {date}")
    return date


def parse_rkms(date: Any) -> str:
    if date == "" or type(date) is not str:
        return ""
    return check_rkms(date)
