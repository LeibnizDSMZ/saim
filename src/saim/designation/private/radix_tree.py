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


def _merge_lead_acr_sep(acr: str, /) -> str:
    # acr is empty or starts with valid char
    if acr == "" or PATTERN_SINGLE_WORD_CHAR.match(acr[0]) is not None:
        return acr
    found = 1
    for pos in range(1, len(acr)):
        if PATTERN_SINGLE_WORD_CHAR.match(acr[pos]) is not None:
            found = pos
            break
    if acr[found:] == "":
        return ""
    return f"{STR_DEFINED_SEP}{acr[found:]}"


@final
class AcrRadixTree:
    """Builds a dictionary hierarchy structure where a word (str) gets split
    like this:
    AcrRT ('ABC#$') -> __con = { 'A' : Acr(BC#$)}
    AcrRT (BC#$)    -> __con = { 'B' : Acr(C#$)}
    AcrRT (C#$)     -> __con = { 'C' : Acr(#$)}
    AcrRT (#$)      -> __con = { ':' : Acr($)}
    AcrRT ($)       -> __con = { ':' : Acr()} __end == True"""

    __slots__ = ("__con", "__end", "__max", "__ready")

    def __init__(self, init: str, /) -> None:
        mer_init = _merge_lead_acr_sep(init)
        self.__end: bool = len(mer_init) == 0
        self.__ready: bool = False
        self.__con: dict[str, AcrRadixTree] = {}
        self.__max = 1
        if mer_init:
            self.__con = {mer_init[0].upper(): AcrRadixTree(mer_init[1:])}
        super().__init__()

    @property
    def end(self) -> bool:
        return self.__end

    @property
    def max(self) -> int:
        return self.__max

    @property
    def len(self) -> int:
        return len(self.__con)

    def get_next(self, ind: str, /) -> Self | None:
        return self.__con.get(ind, None)

    def add(self, to_add: str, /) -> None:
        if self.__ready:
            return None
        mer_to_add = _merge_lead_acr_sep(to_add)
        if not mer_to_add:
            self.__end = True
            return None

        to_add_k = mer_to_add[0].upper()
        if to_add_k in self.__con:
            self.__con[to_add_k].add(mer_to_add[1:])
        else:
            self.__con[to_add_k] = AcrRadixTree(mer_to_add[1:])

    def compact_able(self) -> tuple[str, Self] | None:
        if len(self.__con) == 1 and not (self.__end or STR_DEFINED_SEP in self.__con):
            return self.__con.popitem()
        return None

    def _compact(self) -> None:
        com_nodes: dict[str, AcrRadixTree] = {}
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
        #  with clean cutoff at the end, including brackets
        #  but not extra chars of any kind
        return self.__origin[0 : mapped_pos + 1]

    def is_clearly_sep(self, char_index: int, /) -> bool:
        if self.__org_len > char_index + 1:
            two_chars = self.__origin[char_index : char_index + 2]
            if _PATTERN_TWO_CHAR.match(two_chars) is not None:
                return False
            if _PATTERN_TWO_NUM.match(two_chars) is not None:
                return False
        return True


def _search_node(
    radix: AcrRadixTree, to_find: str, /
) -> tuple[bool, AcrRadixTree | None]:
    node = radix.get_next(to_find)
    if node is None:
        return False, node
    return node.end, node


def _search(radix: AcrRadixTree, to_find: _SOMap, start: int, /) -> int:
    to_sea = to_find.short_seq[start : start + radix.max]
    if not to_sea:
        return -1
    max_ind = len(to_sea)
    for ind in range(0, max_ind):
        sea_sub = to_sea[0 : max_ind - ind]
        end_node, next_node = _search_node(radix, sea_sub)
        if next_node:
            next_start = start + max_ind - ind
            mom_pos = next_start - 1
            next_res = _search(next_node, to_find, next_start)
            if next_res != -1:
                return next_res
            if end_node and to_find.is_clearly_sep(mom_pos):
                return mom_pos
            return -1
    return -1


def is_acr_or_code(radix: AcrRadixTree, to_sea: str, /) -> bool:
    radix.compact()
    f_sea = to_sea.upper()
    f_sea_fixed = replace_non_word_chars(f_sea)
    if f_sea_fixed == "":
        return False
    mapper = _SOMap(f_sea, f_sea_fixed)
    return _search(radix, mapper, 0) == len(to_sea) - 1


def search_acr_or_code_ccno(radix: AcrRadixTree, to_sea: str, /) -> str:
    radix.compact()
    f_sea = to_sea.upper()
    f_sea_fix = replace_non_word_chars(f_sea[0:-1])
    if f_sea_fix == "":
        return ""
    mapper = _SOMap(f_sea[0:-1], f_sea_fix)
    found_pos = _search(radix, mapper, 0)
    return mapper.map_seq(found_pos)
