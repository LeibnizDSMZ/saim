from typing import Iterable

from saim.shared.parse.string import PATTERN_SEP_R
from saim.shared.search.radix_tree import RadixTree, find_first_match


def extract_taxa_from_text(
    text: str, radix: RadixTree[int], jump: int, /
) -> Iterable[int]:
    word = False
    skip = 0
    results: set[int] = set()
    for pos, char in enumerate(text):
        if skip > 0:
            skip -= 1
        if (sep := PATTERN_SEP_R.match(char)) is None and word:
            continue
        elif sep is not None:
            word = False
            continue

        res = find_first_match(radix, text[pos:], False)
        word = len(res) > 0
        skip = jump if len(res) > 0 else 0
        results.update(rid for _, ids in res for rid in ids)
    yield from results
