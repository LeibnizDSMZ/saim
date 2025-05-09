from collections import defaultdict
import re

from re import Pattern
from typing import final, Final, Self

from saim.shared.parse.string import (
    PATTERN_SINGLE_WORD_CHAR,
    STR_DEFINED_SEP,
    replace_non_word_chars,
)


_SET_BRACETS_CLOSE: Final[set[str]] = {")", "]"}
_PATTERN_TWO_CHAR: Final[Pattern[str]] = re.compile(r"^[A-Za-z]{2}$")
_PATTERN_TWO_NUM: Final[Pattern[str]] = re.compile(r"^[0-9]{2}$")


def _merge_lead_string_sep(string: str, /) -> str:
    # string is empty or starts with valid char
    if string == "" or PATTERN_SINGLE_WORD_CHAR.match(string[0]) is not None:
        return string
    found = 1
    for pos in range(1, len(string)):
        if PATTERN_SINGLE_WORD_CHAR.match(string[pos]) is not None:
            found = pos
            break
    if string[found:] == "":
        return ""
    return f"{STR_DEFINED_SEP}{string[found:]}"


@final
class RadixTree[T]:
    """Builds a dictionary hierarchy structure where a word (str) gets split
    like this:
    AcrRT ('ABC#$') -> __con = { 'A' : Acr(BC#$)}
    AcrRT (BC#$)    -> __con = { 'B' : Acr(C#$)}
    AcrRT (C#$)     -> __con = { 'C' : Acr(#$)}
    AcrRT (#$)      -> __con = { ':' : Acr($)}
    AcrRT ($)       -> __con = { ':' : Acr()} __end == True"""

    __slots__ = ("__con", "__end", "__index", "__max", "__ready")

    def __init__(self, init: str, index: tuple[T] | None = None, /) -> None:
        mer_init = _merge_lead_string_sep(init)
        self.__end: bool = len(mer_init) == 0
        self.__index: set[T] = set()
        if index is not None and self.__end:
            self.__index.update(index)
        self.__ready: bool = False
        self.__con: dict[str, RadixTree[T]] = {}
        self.__max = 1
        if mer_init:
            self.__con = {mer_init[0].upper(): RadixTree[T](mer_init[1:], index)}
        super().__init__()

    @property
    def end(self) -> bool:
        return self.__end

    @property
    def index(self) -> set[T]:
        return self.__index

    @property
    def max(self) -> int:
        return self.__max

    @property
    def len(self) -> int:
        return len(self.__con)

    def get_next(self, ind: str, /) -> Self | None:
        return self.__con.get(ind, None)

    def add(self, to_add: str, index: tuple[T] | None = None, /) -> None:
        if self.__ready:
            return None
        mer_to_add = _merge_lead_string_sep(to_add)
        if not mer_to_add:
            self.__end = True
            if index is not None:
                self.index.update(index)
            return None

        to_add_k = mer_to_add[0].upper()
        if to_add_k in self.__con:
            self.__con[to_add_k].add(mer_to_add[1:], index)
        else:
            self.__con[to_add_k] = RadixTree[T](mer_to_add[1:], index)

    def compact_able(self) -> tuple[str, Self] | None:
        if len(self.__con) == 1 and not (self.__end or STR_DEFINED_SEP in self.__con):
            return self.__con.popitem()
        return None

    def _compact(self) -> None:
        com_nodes: dict[str, RadixTree[T]] = {}
        rm_keys: set[str] = set()
        for key, node in self.__con.items():
            node.compact()
            if key != STR_DEFINED_SEP and (to_merge := node.compact_able()) is not None:
                rm_keys.add(key)
                new_k = f"{key}{to_merge[0]}"
                com_nodes[new_k] = to_merge[1]
        for to_rm in rm_keys:
            del self.__con[to_rm]
        for key, node in com_nodes.items():
            self.__con[key] = node
            if len(key) > self.__max:
                self.__max = len(key)

    def compact(self) -> None:
        if not self.__ready:
            self._compact()
            self.__ready = True

    @property
    def keys(self) -> list[str]:
        return list(self.__con.keys())


@final
class _SOMap:
    __slots__ = ("__map_seq", "__org_len", "__origin", "__short")

    def __init__(self, origin: str, short: str, /) -> None:
        super().__init__()
        self.__map_seq = {}  # mapping idx of short on idx of origin
        self.__origin = origin
        self.__org_len = len(self.__origin)
        self.__short = short
        running_offset = 0
        for sh_i, char in enumerate(short):
            while char != origin[running_offset + sh_i] and char != STR_DEFINED_SEP:
                running_offset += 1
            self.__map_seq[sh_i] = running_offset + sh_i

    @property
    def short_seq(self) -> str:
        return self.__short

    def map_seq(self, last_ind: int, /) -> str:
        if last_ind == -1:
            return ""
        # last_ind = idx of short
        # mapped_pos = equivalent pos in origin
        mapped_pos = self.__map_seq[last_ind]
        if (
            self.__org_len > mapped_pos + 1
            and self.__origin[mapped_pos + 1] in _SET_BRACETS_CLOSE
        ):
            mapped_pos += 1
        # return the full original until the end of short,
        # with clean cutoff at the end, including brackets
        # but not extra chars of any kind
        return self.__origin[0 : mapped_pos + 1]

    def is_clearly_sep(self, char_index: int, /) -> bool:
        if self.__org_len > char_index + 1:
            two_chars = self.__origin[char_index : char_index + 2]
            if _PATTERN_TWO_CHAR.match(two_chars) is not None:
                return False
            if _PATTERN_TWO_NUM.match(two_chars) is not None:
                return False
        return True


def _search_node[
    T
](radix: RadixTree[T], to_find: str, /) -> tuple[bool, set[T], RadixTree[T] | None]:
    node = radix.get_next(to_find)
    if node is None:
        return False, set(), node
    return node.end, node.index, node


def _search[
    T
](
    radix: RadixTree[T],
    to_find: _SOMap,
    start: int,
    container: defaultdict[int, set[T]],
    /,
) -> None:
    to_sea = to_find.short_seq[start : start + radix.max]
    if to_sea != "":
        max_ind = len(to_sea)
        for ind in range(0, max_ind):
            sea_sub = to_sea[0 : max_ind - ind]
            end_node, end_index, next_node = _search_node(radix, sea_sub)
            if next_node:
                next_start = start + max_ind - ind
                mom_pos = next_start - 1
                _search(next_node, to_find, next_start, container)
                if end_node and to_find.is_clearly_sep(mom_pos) and mom_pos > 0:
                    container[mom_pos].update(end_index)


def is_full_match[T](radix: RadixTree[T], to_sea: str, /) -> tuple[bool, set[T]]:
    radix.compact()
    f_sea = to_sea.upper()
    f_sea_fixed = replace_non_word_chars(f_sea)
    if f_sea_fixed == "":
        return False, set()
    mapper = _SOMap(f_sea, f_sea_fixed)
    found_pos: defaultdict[int, set[T]] = defaultdict(set)
    _search(radix, mapper, 0, found_pos)
    if len(found_pos) > 0 and (last_id := max(found_pos)) == len(to_sea) - 1:
        return True, found_pos.get(last_id, set())
    return False, set()


def find_first_match[
    T
](radix: RadixTree[T], to_sea: str, trim_right: bool = True, /) -> list[
    tuple[str, set[T]]
]:
    radix.compact()
    f_sea = to_sea.upper()
    if trim_right:
        f_sea = f_sea[0:-1]
    f_sea_fix = replace_non_word_chars(f_sea)
    if f_sea_fix == "":
        return []
    mapper = _SOMap(f_sea, f_sea_fix)
    found_pos: defaultdict[int, set[T]] = defaultdict(set)
    _search(radix, mapper, 0, found_pos)
    return [(mapper.map_seq(pos), index) for pos, index in found_pos.items()]
