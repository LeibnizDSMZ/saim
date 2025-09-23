import re

from re import Pattern
from typing import Iterable, final, Final

from saim.shared.parse.string import (
    PATTERN_SINGLE_WORD_CHAR_R,
    STR_DEFINED_SEP,
    replace_non_word_chars,
    replace_non_word_chars_iter,
)


_SET_BRACETS_CLOSE: Final[set[str]] = {")", "]"}
_PATTERN_TWO_CHAR: Final[Pattern[str]] = re.compile(r"^[A-Za-z]{2}$")
_PATTERN_TWO_NUM: Final[Pattern[str]] = re.compile(r"^[0-9]{2}$")


def _merge_lead_string_sep(string: str, /) -> str:
    # string is empty or starts with valid char
    if string == "" or PATTERN_SINGLE_WORD_CHAR_R.match(string[0]) is not None:
        return string
    found = 1
    for pos in range(1, len(string)):
        if PATTERN_SINGLE_WORD_CHAR_R.match(string[pos]) is not None:
            found = pos
            break
    if string[found:] == "":
        return ""
    return f"{STR_DEFINED_SEP}{string[found:]}"


type _RQP[T] = tuple[str, RadixTree[T]]


@final
class RadixTree[T]:
    """Builds a dictionary hierarchy structure where a word (str) gets split
    like this:
    AcrRT ('ABC#$') -> __con = { 'A' : Acr(BC#$)}
    AcrRT (BC#$)    -> __con = { 'B' : Acr(C#$)}
    AcrRT (C#$)     -> __con = { 'C' : Acr(#$)}
    AcrRT (#$)      -> __con = { ':' : Acr($)}
    AcrRT ($)       -> __con = { ':' : Acr()} __end == True"""

    __slots__ = ("con", "end", "index", "max", "ready")

    def __init__(self, init: str, index: tuple[T, ...], /) -> None:
        mer_init = _merge_lead_string_sep(init)
        self.end: bool = len(mer_init) == 0
        self.index: tuple[T, ...] = tuple()
        if index is not None and self.end:
            self.index = index
        self.ready: bool = False
        self.con: tuple[_RQP[T], ...] = tuple()
        self.max = 1
        if mer_init:
            self.con = ((mer_init[0].upper(), RadixTree[T](mer_init[1:], index)),)
        super().__init__()


def _sep_in_con[T](radix: RadixTree[T], /) -> bool:
    for ite in radix.con:
        if ite[0] == STR_DEFINED_SEP:
            return True
    return False


def _compact_able[T](radix: RadixTree[T], /) -> tuple[str, RadixTree[T]] | None:
    if len(radix.con) == 1 and not (radix.end or _sep_in_con(radix)):
        last_item = radix.con[0]
        radix.con = tuple()
        return last_item
    return None


def _iter_com_nodes[T](radix: RadixTree[T], rm_keys: list[str], /) -> Iterable[_RQP[T]]:
    for key, node in radix.con:
        radix_compact(node)
        if key != STR_DEFINED_SEP and (to_merge := _compact_able(node)) is not None:
            rm_keys.append(key)
            new_k = f"{key}{to_merge[0]}"
            yield new_k, to_merge[1]


def _iter_merge_nodes[T](
    radix: RadixTree[T], com_nodes: tuple[_RQP[T], ...], rm_keys: list[str], /
) -> Iterable[_RQP[T]]:
    for ite in radix.con:
        if ite[0] not in rm_keys:
            yield ite
    for ite in com_nodes:
        if len(ite[0]) > radix.max:
            radix.max = len(ite[0])
        yield ite


def _compact[T](radix: RadixTree[T], /) -> None:
    rm_keys: list[str] = []
    com_nodes: tuple[_RQP[T], ...] = tuple(_iter_com_nodes(radix, rm_keys))
    radix.con = tuple(_iter_merge_nodes(radix, com_nodes, rm_keys))


def radix_get_next[T](radix: RadixTree[T], ind: str, /) -> RadixTree[T] | None:
    for ite in radix.con:
        if ite[0] == ind:
            return ite[1]
    return None


def _append_2_tuple_iter[T](
    data: tuple[_RQP[T], ...], to_add_k: str, to_add_v: str, index: tuple[T, ...], /
) -> Iterable[_RQP[T]]:

    append = True
    for ite in data:
        if ite[0] == to_add_k:
            radix_add(ite[1], to_add_v, index)
            append = False
        yield ite
    if append:
        yield to_add_k, RadixTree[T](to_add_v, index)


def radix_add[T](radix: RadixTree[T], to_add: str, index: tuple[T, ...], /) -> None:
    if radix.ready:
        return None
    mer_to_add = _merge_lead_string_sep(to_add)
    if not mer_to_add:
        radix.end = True
        if len(index) > 0:
            radix.index = tuple(set(radix.index) | set(index))
        return None
    to_add_k = mer_to_add[0].upper()
    radix.con = tuple(_append_2_tuple_iter(radix.con, to_add_k, mer_to_add[1:], index))


def radix_compact[T](radix: RadixTree[T], /) -> None:
    if not radix.ready:
        _compact(radix)
        radix.ready = True


def radix_keys[T](radix: RadixTree[T], /) -> list[str]:
    return list(key for key, _ in radix.con)


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

    def is_clearly_sep(self, pos: int, /) -> bool:
        return _is_clearly_sep(pos, self.__origin)


def _is_clearly_sep(pos: int, text: str, /) -> bool:
    if len(text) > pos + 1:
        two_chars = text[pos : pos + 2]
        if _PATTERN_TWO_CHAR.match(two_chars) is not None:
            return False
        if _PATTERN_TWO_NUM.match(two_chars) is not None:
            return False
    return True


def _search_node[T](
    radix: RadixTree[T], to_find: str, /
) -> tuple[bool, tuple[T, ...], RadixTree[T] | None]:
    node = radix_get_next(radix, to_find)
    if node is None:
        return False, tuple(), node
    return node.end, node.index, node


def _search[T](
    radix: RadixTree[T],
    to_find: _SOMap,
    start: int,
    container: dict[int, tuple[T, ...]],
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
                    container[mom_pos] = end_index


def is_full_match[T](radix: RadixTree[T], to_sea: str, /) -> tuple[bool, tuple[T, ...]]:
    radix_compact(radix)
    f_sea = to_sea.upper()
    f_sea_fixed = replace_non_word_chars(f_sea)
    if f_sea_fixed == "":
        return False, tuple()
    mapper = _SOMap(f_sea, f_sea_fixed)
    found_pos: dict[int, tuple[T, ...]] = dict()
    _search(radix, mapper, 0, found_pos)
    if len(found_pos) > 0 and (last_id := max(found_pos)) == len(to_sea) - 1:
        return True, found_pos.get(last_id, tuple())
    return False, tuple()


def find_first_match_with_fix[T](
    radix: RadixTree[T], to_sea: str, trim_right: bool = True, /
) -> list[tuple[str, tuple[T, ...]]]:
    radix_compact(radix)
    f_sea = to_sea.upper()
    if trim_right:
        f_sea = f_sea[0:-1]
    f_sea_fix = replace_non_word_chars(f_sea)
    if f_sea_fix == "":
        return []
    mapper = _SOMap(f_sea, f_sea_fix)
    found_pos: dict[int, tuple[T, ...]] = dict()
    _search(radix, mapper, 0, found_pos)
    return [(mapper.map_seq(pos), index) for pos, index in found_pos.items()]


def _create_sea[T](
    radix: RadixTree[T], full_txt: str, start: int, /
) -> Iterable[tuple[str, int]]:
    to_find = iter(replace_non_word_chars_iter(full_txt, start))
    to_sea = 0
    while to_sea < radix.max:
        try:
            iter_char, iter_pos = next(to_find)
            to_sea += 1
            yield iter_char.upper(), iter_pos
        except StopIteration:
            break


def _search_simple[T](
    radix: RadixTree[T], full_txt: str, start: int, /
) -> Iterable[tuple[T, ...]]:
    to_sea_con = tuple(_create_sea(radix, full_txt, start))
    max_ind = len(to_sea_con)
    if max_ind > 0:
        for ind in range(0, max_ind):
            sea_sub = "".join(txt for txt, *_ in to_sea_con[0 : max_ind - ind])
            end_node, end_index, next_node = _search_node(radix, sea_sub)
            if next_node:
                *_, mom_pos = to_sea_con[max_ind - ind - 1]
                next_start = mom_pos + 1
                for next_node_res in _search_simple(next_node, full_txt, next_start):
                    yield next_node_res
                if end_node and _is_clearly_sep(mom_pos, full_txt) and mom_pos > 0:
                    yield end_index


def find_first_match_simple[T](
    radix: RadixTree[T], to_sea: str, pos: int, /
) -> Iterable[tuple[T, ...]]:
    radix_compact(radix)
    yield from _search_simple(radix, to_sea, pos)
