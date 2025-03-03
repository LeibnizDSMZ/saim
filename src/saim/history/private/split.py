import re
from typing import Final, Iterable

from saim.designation.extract_ccno import clean_designation

_SPLITTER_R: Final[re.Pattern[str]] = re.compile(r"<\W*")
_SPLITTER_L: Final[re.Pattern[str]] = re.compile(r"\W*>")
_SPLITTER_WORD: Final[re.Pattern[str]] = re.compile(r"[,;]+")
_CON_WORD: Final[re.Pattern[str]] = re.compile(r"\w+")


def split_history(history: str, /) -> list[str]:
    if len(his := _SPLITTER_R.split(history)) > 0:
        return his
    if len(his := _SPLITTER_L.split(history)) > 0:
        his.reverse()
        return his
    return [history]


def split_history_event(history_element: str, /) -> Iterable[str]:
    for inf in _SPLITTER_WORD.split(history_element):
        cleaned = clean_designation(inf)
        if _CON_WORD.search(cleaned) is not None:
            yield cleaned
