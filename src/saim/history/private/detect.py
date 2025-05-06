from typing import Iterable, final
from saim.designation.extract_ccno import (
    extract_ccno_from_text,
    get_syn_eq_struct,
)
from saim.designation.known_acr_db import identify_acr_or_code
from saim.shared.data_con.brc import BrcContainer
from saim.shared.data_con.history import HistoryDeposition


def _detect_culture_collection(
    event: str, culture_collection: BrcContainer, /
) -> Iterable[HistoryDeposition]:
    for ccno_des in extract_ccno_from_text(event, culture_collection):
        if ccno_des.acr == "":
            continue
        yield HistoryDeposition(
            cc_ids=set(
                cc_id for cc_id in identify_acr_or_code(ccno_des.acr, culture_collection)
            ),
            designation=get_syn_eq_struct(ccno_des.designation),
            full_designation=ccno_des.designation,
        )
    cc_ids = identify_acr_or_code(event, culture_collection)
    if len(cc_ids) != 0:
        yield HistoryDeposition(cc_ids=cc_ids, designation=None)


@final
class _CreateDesEvents:
    __slots__ = ("__designation", "__full_designation", "__unknown")

    def __init__(self) -> None:
        super().__init__()
        self.__unknown = True
        self.__designation: tuple[str, str, str] | None = None
        self.__full_designation: str = ""

    @property
    def is_unknown(self) -> bool:
        return self.__unknown

    @property
    def designation(self) -> tuple[str, str, str] | None:
        return self.__designation

    @property
    def full_designation(self) -> str:
        return self.__full_designation

    def create_designation_events(
        self, event: list[str], culture_collection: BrcContainer, /
    ) -> Iterable[HistoryDeposition]:
        seen_cc: set[int] = set()
        for ele in event:
            for detected in _detect_culture_collection(ele, culture_collection):
                yield detected
                if len(seen_cc) == 0:
                    seen_cc = detected.cc_ids
                elif len(seen_cc & detected.cc_ids) == 0:
                    self.__unknown = True
                    return None
                if self.__designation is None:
                    self.__designation = detected.designation
                    self.__full_designation = detected.full_designation
                elif (
                    detected.designation is not None
                    and self.__designation != detected.designation
                ):
                    self.__unknown = True
                    return None
        self.__unknown = len(seen_cc) == 0


def detect_culture_collections(
    event: list[str],
    cc_des: dict[int, list[tuple[str, str, str, str]]],
    culture_collection: BrcContainer,
    /,
) -> HistoryDeposition | None:
    gen = _CreateDesEvents()
    cur_res = HistoryDeposition()
    for hist in gen.create_designation_events(event, culture_collection):
        cur_res.cc_ids |= hist.cc_ids
    if gen.is_unknown:
        return None
    cur_res.designation = gen.designation
    cur_res.full_designation = gen.full_designation
    if (
        cur_res.designation is None
        and len(cc_id_s := cc_des.keys() & cur_res.cc_ids) == 1
        and len(cc_des.get(cc_id := cc_id_s.pop(), [])) == 1
    ):
        cur_res.designation = cc_des[cc_id][0][1:]
        cur_res.full_designation = cc_des[cc_id][0][0]
    return cur_res
