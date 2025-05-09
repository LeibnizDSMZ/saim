from collections.abc import Iterable
import re

from re import Pattern
from typing import Any, Final, Never
from cafi.container.acr_db import AcrCoreReg
from saim.designation.known_acr_db import (
    identify_acr,
    rm_complex_structure,
)
from saim.shared.parse.string import (
    PATTERN_CORE_ID_R,
    PATTERN_CORE_ID_EDGE_R,
    PATTERN_CORE_ID_TXT_R,
    PATTERN_EDGE_R,
    PATTERN_ID_EDGE_R,
    PATTERN_LEAD_ZERO_R,
    PATTERN_SEP,
    PATTERN_THREE_GROUPS_R,
    PATTERN_PREFIX_START_R,
    clean_string,
)
from saim.shared.data_con.brc import BrcContainer
from saim.shared.data_con.designation import (
    ALL_DES_TYPES,
    STRAIN_INFO_SI_DP_REG,
    STRAIN_INFO_SI_ID_REG,
    DesignationType,
    CCNoDes,
    CCNoId,
)
from saim.shared.error.exceptions import DesignationEx
from saim.shared.search.radix_tree import RadixTree, find_first_match_with_fix

DEF_SUF_RM: Final[tuple[str, ...]] = (r"T", r"\s")
_SUF_CLEAN: Final[tuple[Pattern[str], ...]] = (re.compile(r"T$"),)
_PATTERN_PARA: Final[Pattern[str]] = re.compile(r"\(.*\)|\[.*]|<.*>")
_PATTERNS_DES_CL: Final[tuple[Pattern[str], ...]] = (
    re.compile(r"^([Tt]ype[-\s]+)?[Ss]train[.:\s]+"),
    re.compile(r"^([Ss]pecimen[-\s]+)?[Vv]oucher[.:\s]+"),
    re.compile(r"^([Cc]ulture[-\s]+)?[Cc]ollection[.:\s]+"),
    re.compile(rf"[{''.join(DEF_SUF_RM)}]+$"),
)
_SET_ONE_DIG_NUMS: Final[set[str]] = {str(num) for num in range(10)}


def get_ccno_acr(
    ccno: str, radix: RadixTree[Never], trim_right: bool = True, /
) -> Iterable[str]:
    try:
        for mat, _ in find_first_match_with_fix(radix, ccno, trim_right):
            yield mat
    except ValueError as exc:
        raise DesignationEx(f"[{ccno}] could not find acr") from exc


def get_ccno_id(ccno: str, acr: str, /) -> str:
    acr_cl = re.compile(r"^" + re.escape(acr), re.I)
    fixed_id = clean_string(ccno, acr_cl, _PATTERN_PARA, PATTERN_ID_EDGE_R)
    if acr == "" or fixed_id == "":
        raise DesignationEx(f"[{ccno}] acr or id are empty - acr[{acr}] id [{fixed_id}]")
    id_reg = re.compile(r"^" + re.escape(acr) + r"[^A-Za-z].*$", re.I)
    if acr[-1] in _SET_ONE_DIG_NUMS:
        id_reg = re.compile(r"^" + re.escape(acr) + r"\D.*$")
    if id_reg.match(ccno) is None:
        raise DesignationEx(
            f"[{ccno}] id is strangely connected to acr - acr[{acr}] id[{fixed_id}]"
        )
    return fixed_id


def _cl_core(core: str, /) -> str:
    return clean_string(core, PATTERN_CORE_ID_EDGE_R, PATTERN_LEAD_ZERO_R)


def _cl_id(cid: str, /) -> str:
    return clean_string(cid, PATTERN_ID_EDGE_R)


def _extract_suf_pre(to_check: str, allowed: str, /) -> str:
    if to_check == "":
        return ""
    res = re.compile(rf"({allowed})")
    for suf_pre in res.finditer(to_check):
        if suf_pre[0] != "":
            return suf_pre[0]
    return ""


def _is_reasonable_suf(suf: Any, brc_reg: AcrCoreReg, /) -> tuple[bool, str]:
    if not isinstance(suf, str):
        return False, ""
    suf_e = _extract_suf_pre(suf, brc_reg.suf)
    suf_cl = clean_string(suf, PATTERN_ID_EDGE_R)
    if suf_cl != "" and suf_cl != suf_e and clean_string(suf_cl, *_SUF_CLEAN) != suf_e:
        return False, ""
    return True, suf_e


def _is_reasonable_pre(pre: Any, brc_reg: AcrCoreReg, /) -> tuple[bool, str]:
    if not isinstance(pre, str):
        return False, ""
    pre_e = _extract_suf_pre(pre, brc_reg.pre)
    pre_cl = clean_string(pre, PATTERN_ID_EDGE_R)
    if pre_cl != "" and pre_e != pre_cl:
        return False, ""
    return True, pre_e


def _get_id_parts_known(
    brc_reg_con: list[AcrCoreReg], fix_id: str, /
) -> tuple[str, str, str] | None:
    for brc_reg in brc_reg_con:
        mat = re.compile(rf"^(.*?)({brc_reg.core})(.*?)$").match(fix_id)
        if mat is None or (core := mat.group(2)) is None:
            continue
        pre, core, *_, suf = mat.groups()
        if PATTERN_CORE_ID_R.match(core) is None:
            continue
        rea_p, pre = _is_reasonable_pre(pre, brc_reg)
        rea_s, suf = _is_reasonable_suf(suf, brc_reg)
        if not (rea_p and rea_s):
            continue
        return pre, _cl_core(core), suf
    return None


def _split_acr_id(ccno: str, acr: str, /) -> tuple[str, str] | None:
    try:
        fixed_id = get_ccno_id(ccno, acr)
    except DesignationEx:
        return None
    return acr, fixed_id


def _identify_ccno(
    ccno: str,
    brc: BrcContainer,
    acr: str,
    /,
) -> CCNoDes:
    clean_ccno = clean_designation(ccno)
    if (res_no := _split_acr_id(clean_ccno, acr)) is None:
        return CCNoDes(designation=clean_ccno)
    brc_acr, fixed_id = res_no
    brc_reg_con = [brc.cc_db[a_id].regex_id for a_id in identify_acr(brc_acr, brc)]
    if (res_id := _get_id_parts_known(brc_reg_con, _cl_id(fixed_id))) is None:
        return CCNoDes(designation=clean_ccno)
    pre, core, suf = res_id
    return CCNoDes(
        acr=brc_acr,
        id=CCNoId(full=fixed_id, pre=pre, core=core, suf=suf),
        designation=clean_ccno,
    )


def _add_suffix(full_suf: str, clean_suf: str, /) -> str:
    consumed = 0
    suf_iter = iter(full_suf)
    for char in clean_suf:
        search = True
        while search:
            suf_char = next(suf_iter)
            consumed += 1
            if suf_char.upper() == char.upper():
                search = False
    return full_suf[:consumed]


def _identify_ccno_fix(
    acr: str,
    ccno: str,
    suffix: str,
    brc: BrcContainer,
    /,
) -> CCNoDes:
    clean_ccno = clean_designation(ccno)
    if (res_no := _split_acr_id(clean_ccno, acr)) is None:
        return CCNoDes(designation=clean_ccno)
    brc_acr, fixed_id = res_no
    fixed_id_cl = _cl_id(fixed_id)
    pre, core, suf = ["", "", ""]
    for brc_reg in [brc.cc_db[a_id].regex_id for a_id in identify_acr(brc_acr, brc)]:
        if (
            brc_reg.suf != ""
            and (suf_mat := re.compile(rf"^({PATTERN_SEP}?{brc_reg.suf})").search(suffix))
            is not None
        ):
            fixed_id_cl += suf_mat.group(1)
        if (res_id := _get_id_parts_known([brc_reg], fixed_id_cl)) is not None:
            pre, core, suf = res_id
            break
    if core == "":
        return CCNoDes(designation=clean_ccno)
    if suf != "":
        to_add = _add_suffix(suffix, suf)
        clean_ccno += to_add
        fixed_id += to_add
    return CCNoDes(
        acr=brc_acr,
        id=CCNoId(full=fixed_id, pre=pre, core=core, suf=suf),
        designation=clean_ccno,
    )


def _identify_left_ccno(
    rev_acr: str,
    rev_pre: str,
    left: str,
    /,
) -> str:
    consumed = 0
    left_iter = iter(left)
    for char in [*rev_pre, *rev_acr]:
        search = True
        while search:
            left_char = next(left_iter)
            consumed += 1
            if left_char.upper() == char.upper():
                search = False
    return left[consumed - 1 :: -1]


def _identify_valid_ccno(ccno: str, brc: BrcContainer, /) -> Iterable[CCNoDes]:
    try:
        for mem_acr in get_ccno_acr(ccno, brc.kn_acr, True):
            ccno_des = _identify_ccno(ccno, brc, mem_acr)
            if ccno_des.acr != "":
                yield ccno_des
    except DesignationEx:
        return None


def identify_ccno(ccno: str, brc: BrcContainer, /) -> CCNoDes:
    for ccno_des in sorted(
        _identify_valid_ccno(ccno, brc), key=lambda val: -len(val.acr)
    ):
        return ccno_des
    return CCNoDes(designation=ccno)


def identify_all_valid_ccno(ccno: str, brc: BrcContainer, /) -> list[CCNoDes]:
    return [ccno_des for ccno_des in _identify_valid_ccno(ccno, brc)]


def _identify_designation_types(designation: CCNoDes, /) -> Iterable[DesignationType]:
    if designation.acr != "" and designation.id.core != "":
        yield DesignationType.ccno
    des_clean = clean_string(
        designation.designation, _PATTERN_PARA, PATTERN_EDGE_R, *_PATTERNS_DES_CL
    )
    for typ, pats in ALL_DES_TYPES:
        for reg in pats:
            if reg.match(des_clean) is not None:
                yield typ
                break


def identify_designation_type(designation: CCNoDes, /) -> DesignationType:
    for typ in _identify_designation_types(designation):
        return typ
    return DesignationType.des


def identify_designation_types(designation: CCNoDes, /) -> list[DesignationType]:
    types = [typ for typ in _identify_designation_types(designation)]
    if len(types) > 0:
        return types
    return [DesignationType.des]


def identify_designation(
    designation: str, brc: BrcContainer, /
) -> tuple[DesignationType, CCNoDes]:
    ccno_like = identify_ccno(designation, brc)
    return identify_designation_type(ccno_like), ccno_like


def get_si_id(designation: str, /) -> tuple[int, int] | None:
    trimmed = designation.strip()
    for reg in STRAIN_INFO_SI_ID_REG:
        if (mat := reg.match(trimmed)) is not None:
            return int(mat.group(1)), 1 if ((ver := mat.group(2)) is None) else int(ver)
    return None


def get_si_cu(designation: str, /) -> int:
    trimmed = designation.strip()
    for reg in STRAIN_INFO_SI_DP_REG:
        if (mat := reg.match(trimmed)) is not None:
            return int(mat.group(1))
    return -1


def get_syn_eq_struct(designation: str, /) -> tuple[str, str, str]:
    clean_des = clean_designation(designation)
    syn_eq = PATTERN_THREE_GROUPS_R.match(clean_des)
    if syn_eq is None:
        return "", "", ""
    pre, core, suf, *_ = syn_eq.groups()
    if (
        isinstance(pre, str)
        and isinstance(core, str)
        and isinstance(suf, str)
        and core != ""
    ):
        return (
            rm_complex_structure(pre),
            clean_string(core, PATTERN_CORE_ID_EDGE_R),
            clean_string(suf, PATTERN_ID_EDGE_R, *_SUF_CLEAN).upper(),
        )
    return "", "", ""


def clean_designation(designation: str, /) -> str:
    return clean_string(designation, _PATTERN_PARA, PATTERN_EDGE_R, *_PATTERNS_DES_CL)


def _get_acronyms(
    left: str, pre_end: int, prefix: str, brc: BrcContainer, /
) -> Iterable[tuple[str, str]]:
    for acr in get_ccno_acr(left, brc.kn_acr_rev, False):
        yield acr, ""
    new_start = clean_string(left[pre_end:], PATTERN_EDGE_R)
    for acr in get_ccno_acr(new_start, brc.kn_acr_rev, False):
        yield acr, prefix


def extract_ccno_from_text(text: str, brc: BrcContainer, /) -> Iterable[CCNoDes]:
    last_end = 0
    for match in PATTERN_CORE_ID_TXT_R.finditer(text):
        last_end = max(last_end, match.start(1) - 64)
        left_full = text[last_end : match.start(1)][::-1]
        sub_left = clean_string(left_full, PATTERN_EDGE_R)
        rev_pre = PATTERN_PREFIX_START_R.search(sub_left)
        if rev_pre is None:
            continue
        sub_right = text[match.end(1) : match.end(1) + 9]
        for rev_acr_d, rev_pre_d in _get_acronyms(
            sub_left, rev_pre.end(1), rev_pre.group(1), brc
        ):
            ccno_left = _identify_left_ccno(rev_acr_d, rev_pre_d, left_full)
            if ccno_left == "":
                continue
            ccno_des = _identify_ccno_fix(
                rev_acr_d[::-1], ccno_left + match.group(1), sub_right, brc
            )
            if ccno_des.acr != "":
                yield ccno_des
        last_end = match.end(1)
