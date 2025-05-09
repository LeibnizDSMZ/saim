import re

from re import Pattern
from typing import Final, Any

from saim.shared.error.exceptions import DesignationEx


STR_DEFINED_SEP: Final[str] = ":"
PATTERN_SEPARATOR_MULTI_R = re.compile(rf"{STR_DEFINED_SEP}+")
PATTERN_SEP: Final[str] = r"[,.:/\s_-]"
PATTERN_SEP_R: Final[Pattern[str]] = re.compile(PATTERN_SEP)
PATTERN_EDGE_R: Final[Pattern[str]] = re.compile(r"^[\W_]+|[\W_]+$")
PATTERN_L_EDGE_R: Final[Pattern[str]] = re.compile(r"^[\W_]+")
PATTERN_ID_EDGE_R: Final[Pattern[str]] = re.compile(rf"^{PATTERN_SEP}+|{PATTERN_SEP}+$")
PATTERN_CORE_ID_EDGE_R: Final[Pattern[str]] = re.compile(r"^\D+|\D+$")
PATTERN_CORE_ID_R: Final[Pattern[str]] = re.compile(r"^\d+(?:\D\d+)*$")
PATTERN_CORE_ID_TXT_R: Final[Pattern[str]] = re.compile(r"(\d+(?:\D\d+)*)")
PATTERN_PREFIX_START_R: Final[Pattern[str]] = re.compile(r"^\W*([A-Za-z]+)\W*")
PATTERN_THREE_GROUPS_R: Final[Pattern[str]] = re.compile(r"^(\D*)(\d+(?:\D\d+)*)(\D*)$")
PATTERN_LEAD_ZERO_R: Final[re.Pattern[str]] = re.compile(r"^0*(?=\d+$)")
PATTERN_SINGLE_WORD_CHAR_R: Final[Pattern[str]] = re.compile(r"^[A-Za-z0-9]$")
PATTERN_TAG_R: Final[Pattern[str]] = re.compile(r"<[^<>]*>")
PATTERN_BRACKETS_RL: Final[tuple[Pattern[str], ...]] = (
    re.compile(r"\([^())]*\)"),
    re.compile(r"\[[^[\]]*\]"),
)
PATTERN_REDUNDANT_SPACE_R: Final[Pattern[str]] = re.compile(r"\s+(?=[\s,.:])")


# new version of all the old functions:
def clean_string(text: str, /, *pattern_args: Pattern[str]) -> str:
    """Takes a string and one or multiple regex patterns,
    returns the string with all occurrences of the patterns replaced by ''"""
    clean_string = text
    for pattern in pattern_args:
        clean_string = pattern.sub("", clean_string)
    return clean_string


def replace_non_word_chars(input_str: str, /) -> str:
    output_str = "".join(
        char if PATTERN_SINGLE_WORD_CHAR_R.match(char) is not None else STR_DEFINED_SEP
        for char in input_str
    )
    return PATTERN_SEPARATOR_MULTI_R.sub(STR_DEFINED_SEP, output_str)


def check_pattern(input_str: str, pattern: Pattern[str], /) -> None:
    if pattern.match(input_str) is None:
        raise DesignationEx(f"String '{input_str}' has an invalid format")


def clean_id_edges(val: Any) -> str:
    if type(val) is str:
        return clean_string(val, PATTERN_ID_EDGE_R)
    return ""


def clean_core_id_edges(val: Any) -> str:
    if type(val) is str:
        return clean_string(val, PATTERN_CORE_ID_EDGE_R)
    return ""


def clean_edges(val: Any) -> str:
    if type(val) is str:
        return clean_string(val, PATTERN_EDGE_R)
    return ""


def trim_edges(val: Any) -> str:
    if type(val) is str:
        return val.strip()
    return ""


def clean_edges_rm_tags(val: Any) -> str:
    if type(val) is str:
        return clean_string(val, PATTERN_TAG_R, PATTERN_EDGE_R)
    return ""


def clean_ledge_rm_tags(val: Any) -> str:
    if type(val) is str:
        return clean_string(val, PATTERN_TAG_R, PATTERN_L_EDGE_R)
    return ""


def clean_text(val: Any) -> str:
    if type(val) is str:
        sample = clean_string(val, PATTERN_REDUNDANT_SPACE_R)
        return sample.strip()
    return ""


def clean_text_rm_tags(val: Any) -> str:
    if type(val) is str:
        sample = clean_string(val, PATTERN_TAG_R)
        return clean_text(sample)
    return ""


def clean_text_rm_enclosing(val: Any) -> str:
    if type(val) is str:
        sample = clean_string(val, PATTERN_TAG_R, *PATTERN_BRACKETS_RL)
        return clean_text(sample)
    return ""
