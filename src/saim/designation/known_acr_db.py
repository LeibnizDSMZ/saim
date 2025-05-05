from collections import defaultdict
import re

from cafi.container.acr_db import AcrDbEntry
from cafi.library.loader import CURRENT_VER, load_acr_db

from saim.designation.private.radix_tree import AcrRadixTree, is_acr_or_code
from saim.shared.parse.string import (
    PATTERN_BRC_SEP_CR_NEW,
    PATTERN_EDGE,
    clean_string,
    replace_non_word_chars,
)
from saim.shared.data_con.brc import AcrDbEntryFixed, BrcContainer


def rm_complex_structure(acr: str, /) -> str:
    slim_acr = replace_non_word_chars(acr)
    return clean_string(slim_acr, PATTERN_BRC_SEP_CR_NEW, PATTERN_EDGE).upper()


def _add_fixed_acr(cc_db: dict[int, AcrDbEntry], /) -> dict[int, AcrDbEntryFixed]:
    cc_db_m = {}
    for cid, cce in cc_db.items():
        if not cce.deprecated:
            cc_db_m[cid] = AcrDbEntryFixed(
                f_acr_syn={rm_complex_structure(acr) for acr in cce.acr_synonym},
                f_acr=rm_complex_structure(cce.acr),
                f_code=rm_complex_structure(cce.code),
            )
    return cc_db_m


def _create_all_valid_acr(cc_db: dict[int, AcrDbEntry]) -> set[str]:
    all_acr = {brc.acr for brc in cc_db.values() if not brc.deprecated}
    all_acr.update(brc.code for brc in cc_db.values() if not brc.deprecated)
    all_acr.update(
        acr for brc in cc_db.values() if not brc.deprecated for acr in brc.acr_synonym
    )
    return all_acr


def _create_all_prefix_regex(
    cc_db: dict[int, AcrDbEntry]
) -> list[tuple[re.Pattern[str], list[int]]]:
    all_pre = defaultdict(list)
    for dbi, dbe in cc_db.items():
        if dbe.regex_id.pre != "":
            all_pre[dbe.regex_id.pre].append(dbi)
    return [(re.compile(pre), ids) for pre, ids in all_pre.items()]


def _create_acr_code_index(
    cc_db: dict[int, AcrDbEntryFixed], /
) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    cc_db_acr: dict[str, set[int]] = defaultdict(set)
    cc_db_code: dict[str, set[int]] = defaultdict(set)
    for cid, cce in cc_db.items():
        cc_db_code[cce.f_code].add(cid)
        cc_db_acr[cce.f_acr].add(cid)
        for acr_syn in cce.f_acr_syn:
            cc_db_acr[acr_syn].add(cid)
    return cc_db_acr, cc_db_code


def create_brc_con(
    version: str = CURRENT_VER,
    /,
) -> BrcContainer:
    acr_db = load_acr_db(version)
    cc_db_m = _add_fixed_acr(acr_db)

    cc_db_acr, cc_db_code = _create_acr_code_index(cc_db_m)
    all_acr = _create_all_valid_acr(acr_db)

    first_acr = all_acr.pop()
    kn_acr = AcrRadixTree(first_acr)
    kn_acr_rev = AcrRadixTree(first_acr[::-1])
    for acr in all_acr:
        kn_acr.add(acr)
        kn_acr_rev.add(acr[::-1])
    kn_acr.compact()
    kn_acr_rev.compact()

    return BrcContainer(
        cc_db=acr_db,
        f_cc_db=cc_db_m,
        f_cc_db_acr=cc_db_acr,
        f_cc_db_code=cc_db_code,
        kn_acr=kn_acr,
        kn_acr_rev=kn_acr_rev,
    )


def identify_brc_code(brc: str, brc_con: BrcContainer, /) -> set[int]:
    fixed = parse_acr_or_code(brc, brc_con)
    if fixed == "":
        return set()
    return brc_con.f_cc_db_code.get(fixed, set())


def identify_acr(acr: str, brc_con: BrcContainer, /) -> set[int]:
    fixed = parse_acr_or_code(acr, brc_con)
    if fixed == "":
        return set()
    return brc_con.f_cc_db_acr.get(fixed, set())


def identify_acr_or_code(acr: str, brc_con: BrcContainer, /) -> set[int]:
    fixed = parse_acr_or_code(acr, brc_con)
    if fixed == "":
        return set()
    return brc_con.f_cc_db_acr.get(fixed, set()) | brc_con.f_cc_db_code.get(fixed, set())


def parse_acr_or_code(acr_or_code: str, brc_con: BrcContainer, /) -> str:
    if is_acr_or_code(brc_con.kn_acr, acr_or_code):
        return rm_complex_structure(acr_or_code)
    return ""
