from typing import Iterable

from saim.shared.parse.string import PATTERN_SEP_R
from saim.shared.search.radix_tree import (
    RadixTree,
    find_first_match_simple,
)


def extract_taxa_from_text(
    text: str, radix: RadixTree[int], jump: int, /
) -> Iterable[int]:
    word = False
    skip = 0
    results: set[int] = set()
    prep_text = text
    for pos, char in enumerate(text):
        if skip > 0:
            skip -= 1
            continue
        if (sep := PATTERN_SEP_R.match(char)) is None and word:
            continue
        elif sep is not None:
            word = False
            continue
        for ids in find_first_match_simple(radix, prep_text, pos):
            results.update(ids)
            skip = jump
        word = True
    yield from results
