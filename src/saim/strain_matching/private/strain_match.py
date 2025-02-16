from collections import defaultdict
from typing import Iterable, Protocol, Sized, final
import warnings
from saim.designation.extract_ccno import get_si_id
from saim.designation.known_acr_db import rm_complex_structure
from saim.designation.manager import AcronymManager
from saim.shared.data_con.strain import StrainCultureId
from saim.shared.data_con.designation import CCNoDesP
from saim.shared.error.warnings import StrainMatchWarn
from saim.strain_matching.private.container import (
    CulMatCon,
    CultureMatch,
)


def _decide_most_voted_related_ccno(
    all_votes: tuple[int, dict[int, int]], /
) -> tuple[list[int], str]:
    voter, votes = all_votes
    msg = ""
    if len(votes) == 0:
        return [], msg
    all_cnt = sum(votes.values())
    sorted_ids = sorted(votes.items(), key=lambda cnt: -1 * cnt[1])
    _, str_voted = next(iter(sorted_ids))
    if str_voted / voter < 0.4:
        msg = f"[VOTE] only {str_voted} CCNos found in relation "
        msg += f"of {voter} CCNos found in the database"
        msg += f" - all voted SI-IDs were {sorted_ids}"
    if str_voted / all_cnt < 0.5:
        msg += f"[VOTE] ambiguous strain id - {str_voted / all_cnt}"
        msg += f" - all voted SI-IDs were {sorted_ids}"
    return [sid for sid, _ in sorted_ids], msg


def _cr_val_ov(*to_ov: set[int]) -> set[int]:
    overlap: set[int] = set()
    for dov in to_ov:
        if len(overlap) == 0 and len(dov) > 0:
            overlap = dov
            continue
        if len(dov) > 0:
            overlap &= dov
    return overlap


def _report_match(msg: str, data: Sized, /) -> str:
    if len(data) > 0:
        return f"{msg} - {data};"
    return ""


def _create_fallback_set(
    direct_rel: set[int],
    rel_ov_ccno: tuple[int, dict[int, int]],
    rel_ov_si_id: set[int],
    /,
) -> set[int]:
    fb_ids = direct_rel | rel_ov_si_id | set(rel_ov_ccno[1].keys())
    return set(filter(lambda sid: sid > 0, fb_ids))


def _create_fall_back_report(
    rel_ccno_sid: list[int], direct_rel: set[int], rel_ov_si_id: set[int]
) -> str:
    ccno_rel = _report_match("ccno relation", rel_ccno_sid)
    dir_rel = _report_match("direct relation", direct_rel)
    si_id_rel = _report_match("SI-ID relation", rel_ov_si_id)
    return ";".join(msg for msg in (ccno_rel, dir_rel, si_id_rel) if msg != "")


def _cr_selection(
    selected: int, fb_ids: set[int], warn_msg: str, fb_rep: str = "", /
) -> tuple[int, list[int], str]:
    fallback = [sid for sid in fb_ids if sid > 0 and sid != selected]
    has_fallback = len(fallback) > 0
    if has_fallback:
        warn_msg += f"[FALLBACK][SI-ID {selected}] detected fallback SI-IDs {fallback}"
    if selected == -1 and has_fallback and fb_rep != "":
        warn_msg += (
            " [SELECT] could not find a distinct strain "
            + f"for culture - FB SI-IDs{fallback}"
        )
    return selected, fallback, warn_msg


def _vote_strain(
    direct_rel: set[int],
    rel_ov_ccno: tuple[int, dict[int, int]],
    rel_ov_si_id: set[int],
    /,
) -> tuple[int, list[int], str]:
    rel_ccno_sid, warn_msg = _decide_most_voted_related_ccno(rel_ov_ccno)
    rel_sid_set = set(rel_ccno_sid)
    fb_ids = _create_fallback_set(direct_rel, rel_ov_ccno, rel_ov_si_id)
    dec = _cr_val_ov(direct_rel, rel_sid_set, rel_ov_si_id)
    if len(dec) == 1:
        return _cr_selection(dec.pop(), fb_ids, warn_msg)
    if len(rel_ov_si_id) == 1:
        return _cr_selection(rel_ov_si_id.pop(), fb_ids, warn_msg)
    for sid in rel_ccno_sid:
        if sid in dec:
            return _cr_selection(sid, fb_ids, warn_msg)
    fb_rep = _create_fall_back_report(rel_ccno_sid, direct_rel, rel_ov_si_id)
    return _cr_selection(-1, fb_ids, warn_msg, fb_rep)


class _CacheProt(Protocol):
    @property
    def si_cu_err(self) -> set[int]: ...
    @property
    def culture_ccno(self) -> dict[tuple[int, str, str, str], StrainCultureId]: ...
    @property
    def si_id(self) -> dict[int, int]: ...
    @property
    def relation_ccno(self) -> dict[tuple[str, str, str, str], dict[int, int]]: ...


@final
class StrainMatch[CT: CultureMatch]:
    __slots__ = (
        "__ca_acr_man",
        "__ca_cul_ccno",
        "__ca_rel_ccno",
        "__ca_si_cu_err",
        "__ca_si_id",
        "__skip",
    )

    def __init__(
        self, cache: _CacheProt, ca_acr_man: AcronymManager, skip: bool, /
    ) -> None:
        self.__ca_rel_ccno = cache.relation_ccno
        self.__ca_cul_ccno = cache.culture_ccno
        self.__ca_si_id = cache.si_id
        self.__ca_si_cu_err = cache.si_cu_err
        self.__ca_acr_man = ca_acr_man
        self.__skip = skip
        super().__init__()

    def __get_mid(self, si_id: int, /) -> int:
        if si_id > 0:
            return self.__ca_si_id[si_id]
        return -1

    def match(self, cul_mat: CulMatCon[CT]) -> CulMatCon[CT]:
        if self.__skip and cul_mat.strain_id > 0 and cul_mat.culture_id > 0:
            return cul_mat
        r_ccno_sid = self.__find_ccno_in_relation(cul_mat.cul)
        r_ccno_ov_sid = self.__find_ccno_relation_overlap(cul_mat.cul)
        r_tcu_ov_sid = self.__find_si_id_relation_overlap(cul_mat.cul)
        si_id_str, fb_ids, w_msg = _vote_strain(r_ccno_sid, r_ccno_ov_sid, r_tcu_ov_sid)
        si_id_cul = self.__get_mid(cul_mat.strain_id)
        sel_si_id = si_id_str
        selection_mis = si_id_cul > 0 and si_id_str != si_id_cul
        if selection_mis:
            sel_si_id = si_id_cul
            if si_id_str > 0 or len(fb_ids) > 0:
                w_msg += (
                    f"[CUL-STR] cul. si-id {si_id_cul} neq. to str. si-id {si_id_str}"
                )
                w_msg += f" fallbacks {fb_ids!s}"
            if si_id_str > 0:
                fb_ids.append(si_id_str)
        if w_msg != "":
            warnings.warn(f"[{cul_mat.cul.ccno}] {w_msg}", StrainMatchWarn, stacklevel=2)
        return CulMatCon(
            strain_id=sel_si_id,
            culture_id=cul_mat.culture_id,
            cul=cul_mat.cul,
            fallback_strain_ids=fb_ids,
        )

    def match_strain(self, designations: Iterable[str]) -> set[int]:
        return {
            si_id_m
            for des in designations
            for ccno in self.__ca_acr_man.identify_ccno_all_valid(des)
            if ccno.acr != ""
            for si_id_m in self.__find_ccno_in_relation(ccno)
        }

    def __find_ccno_in_relation(self, cul: CCNoDesP | CT, /) -> set[int]:
        f_acr = rm_complex_structure(cul.acr)
        match: set[int] = set()
        if f_acr == "":
            return match
        cid = (f_acr, cul.id.pre, cul.id.core, cul.id.suf)
        if cid in self.__ca_rel_ccno:
            match.update(self.__get_mid(sid) for sid in self.__ca_rel_ccno[cid].keys())
        return match

    def __vote_ccno_ov(self, cul_des: CCNoDesP, /) -> set[int]:
        f_acr = rm_complex_structure(cul_des.acr)
        match: set[int] = set()
        if f_acr == "":
            return match
        cid = (f_acr, cul_des.id.pre, cul_des.id.core, cul_des.id.suf)
        if cid in self.__ca_rel_ccno:
            match.update(self.__ca_rel_ccno[cid].keys())
        return match

    def __vote_ccno(self, brc_ids: set[int], cul_des: CCNoDesP, /) -> set[int]:
        return set(
            cul_str.s
            for bid in brc_ids
            if (
                cul_str := self.__ca_cul_ccno.get(
                    (bid, cul_des.id.pre, cul_des.id.core, cul_des.id.suf), None
                )
            )
            is not None
            and cul_str[0] not in self.__ca_si_cu_err
        )

    def __find_ccno_relation_overlap(self, cul: CT, /) -> tuple[int, dict[int, int]]:
        voter = 0
        votes: dict[int, int] = defaultdict(lambda: 0)
        for rel_cul_str in cul.strain.relation:
            rel_cul_all = self.__ca_acr_man.identify_ccno_all_valid(rel_cul_str)
            for rel_cul in rel_cul_all:
                if rel_cul.acr == "":
                    continue
                voter += 1
                voted_on = self.__vote_ccno_ov(rel_cul)
                voted_on.update(
                    self.__vote_ccno(self.__ca_acr_man.identify_acr(rel_cul.acr), rel_cul)
                )
                for str_id in voted_on:
                    votes[self.__get_mid(str_id)] += 1
        return voter, votes

    def __find_si_id_relation_overlap(self, cul: CT, /) -> set[int]:
        si_ids: set[int] = set()
        for rel_cul_str in cul.strain.relation:
            si_id_con = get_si_id(rel_cul_str)
            if si_id_con is None:
                continue
            si_id, _ = si_id_con
            if si_id in self.__ca_si_id:
                si_ids.add(self.__get_mid(si_id))
        if len(si_ids) > 1:
            warnings.warn(
                f"[{cul.ccno}] found more than one SI-ID {si_ids!s}",
                StrainMatchWarn,
                stacklevel=2,
            )
        return si_ids
