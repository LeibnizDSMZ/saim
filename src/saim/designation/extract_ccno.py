from collections.abc import Iterable
import re

from re import Pattern
from typing import Any, Final
from cafi.container.acr_db import AcrCoreReg
from saim.designation.known_acr_db import identify_acr, rm_complex_structure
from saim.designation.private.radix_tree import search_acr_or_code_ccno
from saim.shared.parse.string import (
    PATTERN_CORE_ID,
    PATTERN_CORE_ID_EDGE,
    PATTERN_EDGE,
    PATTERN_ID_EDGE,
    PATTERN_LEAD_ZERO,
    PATTERN_THREE_GROUPS,
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


def get_ccno_acr(ccno: str, brc: BrcContainer, /) -> list[str]:
    try:
        return search_acr_or_code_ccno(brc.kn_acr, ccno)
    except ValueError as exc:
        raise DesignationEx(f"[{ccno}] could not find acr") from exc


def get_ccno_id(ccno: str, acr: str, /) -> str:
    acr_cl = re.compile(r"^" + re.escape(acr), re.I)
    fixed_id = clean_string(ccno, acr_cl, _PATTERN_PARA, PATTERN_ID_EDGE)
    if acr == "" or fixed_id == "":
        raise DesignationEx(f"[{ccno}] acr or id are empty - acr[{acr}] id[{fixed_id}]")
    id_reg = re.compile(r"^" + re.escape(acr) + r"[^A-Za-z].*$", re.I)
    if acr[-1] in _SET_ONE_DIG_NUMS:
        id_reg = re.compile(r"^" + re.escape(acr) + r"\D.*$")
    if id_reg.match(ccno) is None:
        raise DesignationEx(
            f"[{ccno}] id is strangely connected to acr - acr[{acr}] id[{fixed_id}]"
        )
    return fixed_id


def _cl_core(core: str, /) -> str:
    return clean_string(core, PATTERN_CORE_ID_EDGE, PATTERN_LEAD_ZERO)


def _cl_id(cid: str, /) -> str:
    return clean_string(cid, PATTERN_ID_EDGE)


def _extract_suf_pre(to_check: str, allowed: str, /) -> str:
    if to_check == "":
        return ""
    res = re.compile(rf"({allowed})")
    for suf_pre in res.finditer(to_check):
        if suf_pre[0] != "":
            return suf_pre[0]
    return ""


def _is_reasonable_suf_pre(
    pre: Any, suf: Any, brc_reg: AcrCoreReg, /
) -> tuple[bool, str, str]:
    if not (isinstance(pre, str) and isinstance(suf, str)):
        return False, "", ""
    pre_e = _extract_suf_pre(pre, brc_reg.pre)
    pre_cl = clean_string(pre, PATTERN_ID_EDGE)
    suf_e = _extract_suf_pre(suf, brc_reg.suf)
    suf_cl = clean_string(suf, PATTERN_ID_EDGE)
    if pre_cl != "" and pre_e != pre_cl:
        return False, "", ""
    if suf_cl != "" and suf_cl != suf_e and clean_string(suf_cl, *_SUF_CLEAN) != suf_e:
        return False, "", ""
    return True, pre_e, suf_e


def get_id_parts_known(
    acr: str, brc: BrcContainer, fid: str, /
) -> tuple[str, str, str] | None:
    fix_id = _cl_id(fid)
    for a_id in identify_acr(acr, brc):
        brc_reg = brc.cc_db[a_id].regex_id
        mat = re.compile(rf"^(.*?)({brc_reg.core})(.*?)$").match(fix_id)
        if mat is None or (core := mat.group(2)) is None:
            continue
        pre, core, *_, suf = mat.groups()
        if PATTERN_CORE_ID.match(core) is None:
            continue
        rea, pre, suf = _is_reasonable_suf_pre(pre, suf, brc_reg)
        if not rea:
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
    if (res_id := get_id_parts_known(brc_acr, brc, fixed_id)) is None:
        return CCNoDes(designation=clean_ccno)
    pre, core, suf = res_id
    return CCNoDes(
        acr=brc_acr,
        id=CCNoId(full=fixed_id, pre=pre, core=core, suf=suf),
        designation=clean_ccno,
    )


def _identify_valid_ccno(ccno: str, brc: BrcContainer, /) -> Iterable[CCNoDes]:
    try:
        for mem_acr in get_ccno_acr(ccno, brc):
            ccno_des = _identify_ccno(ccno, brc, mem_acr)
            if ccno_des.acr != "":
                yield ccno_des
    except DesignationEx:
        return None


def identify_ccno(ccno: str, brc: BrcContainer, /) -> CCNoDes:
    for ccno_des in _identify_valid_ccno(ccno, brc):
        return ccno_des
    return CCNoDes(designation=ccno)


def identify_all_valid_ccno(ccno: str, brc: BrcContainer, /) -> list[CCNoDes]:
    return [ccno_des for ccno_des in _identify_valid_ccno(ccno, brc)]


def _identify_designation_types(designation: CCNoDes, /) -> Iterable[DesignationType]:
    if designation.acr != "" and designation.id.core != "":
        yield DesignationType.ccno
    des_clean = clean_string(
        designation.designation, _PATTERN_PARA, PATTERN_EDGE, *_PATTERNS_DES_CL
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
    syn_eq = PATTERN_THREE_GROUPS.match(clean_des)
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
            clean_string(core, PATTERN_CORE_ID_EDGE),
            clean_string(suf, PATTERN_ID_EDGE, *_SUF_CLEAN).upper(),
        )
    return "", "", ""


def clean_designation(designation: str, /) -> str:
    return clean_string(designation, _PATTERN_PARA, PATTERN_EDGE, *_PATTERNS_DES_CL)
