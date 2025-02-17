import re
from typing import Callable

from saim.designation.known_acr_db import identify_acr

from saim.shared.parse.string import check_pattern
from saim.shared.data_con.brc import BrcContainer
from saim.shared.data_con.designation import DesignationType
from saim.shared.error.exceptions import DesignationEx
from cafi.container.acr_db import AcrDbEntry


def _verify_regex(
    to_check: str,
    acr: str,
    brc_con: BrcContainer,
    get_regex: Callable[[AcrDbEntry], str],
    /,
) -> None:
    brc_ids = identify_acr(acr, brc_con)
    all_reg = set(
        get_regex(acr_db)
        for brc_id in brc_ids
        if (acr_db := brc_con.cc_db.get(brc_id, None)) is not None
        and not acr_db.deprecated
    )
    all_reg.discard("")
    check_err = 0
    for ccno_reg in all_reg:
        try:
            check_pattern(to_check, re.compile(ccno_reg))
        except DesignationEx:
            check_err += 1
    if len(all_reg) == 0:
        raise DesignationEx(f"{acr} has no regex defined")
    elif len(all_reg) - check_err == 0:
        raise DesignationEx(f"{to_check} has a non standard format")


def verify_ccno(acr: str, ccno: str, brc_con: BrcContainer, /) -> None:
    _verify_regex(ccno, acr, brc_con, lambda con: con.regex_ccno)


def verify_ccno_id(acr: str, ccno_id: str, brc_con: BrcContainer, /) -> None:
    _verify_regex(ccno_id, acr, brc_con, lambda con: con.regex_id.full)


def verify_specific_ccno(brc_id: int, ccno: str, brc_con: BrcContainer, /) -> None:
    ccno_reg = brc_con.cc_db.get(brc_id, None)
    if not (ccno_reg is None or ccno_reg.deprecated):
        check_pattern(ccno, re.compile(ccno_reg.regex_ccno))
    else:
        raise DesignationEx(f"collection - {brc_id} has no regex defined")


def verify_specific_ccno_id(brc_id: int, ccno_id: str, brc_con: BrcContainer, /) -> None:
    ccno_reg = brc_con.cc_db.get(brc_id, None)
    if not (ccno_reg is None or ccno_reg.deprecated):
        check_pattern(ccno_id, re.compile(ccno_reg.regex_id.full))
    else:
        raise DesignationEx(f"collection - {brc_id} has no regex defined")


def is_valid_known_id(acr: str, cid: str, brc_con: BrcContainer, /) -> bool:
    try:
        verify_ccno_id(acr, cid, brc_con)
    except DesignationEx:
        return False
    return True


def is_valid_known_ccno(acr: str, ccno: str, brc_con: BrcContainer, /) -> bool:
    try:
        verify_ccno(acr, ccno, brc_con)
    except DesignationEx:
        return False
    return True


def is_ccno_like(des_type: str, /) -> bool:
    return des_type == str(DesignationType.ccno)
