from re import Pattern
import re
from typing import Any, Callable, Final

from cafi.container.country import CountryCodes

from saim.shared.verify.types import ch_str_float
from saim.shared.parse.string import clean_string, clean_text_rm_enclosing, trim_edges

_PATTERN_BRACKETS: Final[tuple[Pattern[str], ...]] = (
    re.compile(r"^\([^(]*"),
    re.compile(r"^\[[^[]*"),
    re.compile(r"[^(]*\)$"),
    re.compile(r"[^[]*\]$"),
)


def parse_lat_long(lat_long: Any, ch_spec_float: Callable[[str], str]) -> str:
    if lat_long == "" or type(lat_long) is not str:
        return ""
    return ch_spec_float(lat_long)


def check_lat(lat: str, /) -> str:
    ch_str_float(lat, 90.0, "Latitude")
    return lat.strip()


def check_long(long: str, /) -> str:
    ch_str_float(long, 180.0, "Longitude")
    return long.strip()


def check_country_code(code: Any, /) -> str:
    if not isinstance(code, str) or code == "":
        return ""
    if len(code) != 2:
        raise ValueError(f"malformed country code {code}")
    return CountryCodes().is_code(code.upper())


def clean_place_name(place: str) -> str:
    place_edgeless = trim_edges(place)
    if place == "":
        return ""
    places_no_para = clean_text_rm_enclosing(place_edgeless)
    cl_place = clean_string(places_no_para, *_PATTERN_BRACKETS)
    if len(cl_place) < 2:
        return ""
    return cl_place[0].upper() + cl_place[1:]
