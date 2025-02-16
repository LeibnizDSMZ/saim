from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence, final
import warnings
from saim.designation.known_acr_db import rm_complex_structure
from saim.shared.data_con.strain import StrainCultureId
from saim.shared.data_con.designation import CCNoDesP
from saim.shared.error.exceptions import StrainMatchEx
from saim.shared.error.warnings import StrainMatchWarn, UpdateCacheWarn


@final
@dataclass(slots=True, frozen=True, kw_only=True)
class UpdateResults:
    si_id: int = -1
    si_cu: int = -1
    used_in_update: bool = False
    cid: tuple[int, str, str, str] = (-1, "", "", "")
    add_relations: Sequence[CCNoDesP] = field(default_factory=list)
    del_relations: Sequence[CCNoDesP] = field(default_factory=list)


@final
@dataclass(slots=True, frozen=False, kw_only=True)
class MatchCache:
    # tuple[culture_id, strain_id]
    culture_ccno: dict[tuple[int, str, str, str], StrainCultureId] = field(
        default_factory=dict
    )
    relation_ccno: dict[tuple[str, str, str, str], dict[int, int]] = field(
        default_factory=dict
    )
    si_id: dict[int, int] = field(default_factory=dict)
    si_cu_err: set[int] = field(default_factory=set)
    __correct: bool = True

    def __detect_negative_ids(
        self, data: Iterable[int | Iterable[int] | Mapping[int, int]], /
    ) -> None:
        for did in data:
            if isinstance(did, Iterable):
                self.__detect_negative_ids(did)
            elif isinstance(did, Mapping):
                self.__detect_negative_ids(did.keys())
            elif did < 1:
                raise StrainMatchEx("[CA-UPD] detected a negative ID in cache")

    @property
    def status(self) -> bool:
        try:
            self.check_consistency()
        except StrainMatchEx:
            return False
        return self.__correct

    def get_main_id(self, si_id: int, /) -> int:
        main_id = self.si_id.get(si_id, None)
        if main_id is None:
            raise StrainMatchEx(f"[CA-GET] [{si_id}] missing in cache")
        return main_id

    def check_consistency(self) -> None:
        self.__detect_negative_ids(self.culture_ccno.values())
        self.__detect_negative_ids(self.relation_ccno.values())
        self.__detect_negative_ids(self.si_id.values())
        self.__detect_negative_ids(self.si_cu_err)
        for str_ids in self.relation_ccno.values():
            for si_id in str_ids:
                main_id = self.si_id.get(si_id, None)
                if main_id is None or main_id != si_id:
                    raise StrainMatchEx(
                        f"[CA-UPD] [{si_id}] detected a non main SI-ID in ccno relations"
                    )
        for sci in self.culture_ccno.values():
            si_id = sci.s
            main_id = self.si_id.get(si_id, None)
            if main_id is None or main_id != si_id:
                raise StrainMatchEx(
                    f"[CA-UPD] [{si_id}] detected a non main SI-ID in culture ccnos"
                )

    def __add_relation_ccno(self, cid: tuple[str, str, str, str], si_id: int, /) -> None:
        if cid not in self.relation_ccno:
            self.relation_ccno[cid] = {}
        if si_id not in self.relation_ccno[cid]:
            self.relation_ccno[cid][si_id] = 1
        else:
            self.relation_ccno[cid][si_id] += 1

    def __delete_relation_ccno(
        self, cid: tuple[str, str, str, str], si_id: int, /
    ) -> None:
        counter = 1
        if cid in self.relation_ccno:
            try:
                self.relation_ccno[cid][si_id] -= 1
                counter = self.relation_ccno[cid][si_id]
                if counter <= 0:
                    del self.relation_ccno[cid][si_id]
            except KeyError:
                self.__correct = False
                warnings.warn(
                    f"[CA-UPD] [{si_id}] not detected in relation [{cid}]",
                    UpdateCacheWarn,
                    stacklevel=2,
                )
        if counter < 0:
            self.__correct = False
            warnings.warn(
                f"[CA-UPD] [{si_id}] deleted more often than added [{cid}]",
                UpdateCacheWarn,
                stacklevel=2,
            )

    def __add_si_id(self, si_id: int, /) -> None:
        if si_id not in self.si_id:
            self.si_id[si_id] = si_id
        if self.si_id[si_id] != si_id:
            self.__correct = False
            warnings.warn(
                f"[CA-UPD] [{si_id}] return by update does not represent a main id",
                UpdateCacheWarn,
                stacklevel=2,
            )

    def __add_del_relations(
        self, si_id: int, relations: Sequence[CCNoDesP], add: bool, /
    ) -> None:
        mem = set()
        for rel in relations:
            f_acr = rm_complex_structure(rel.acr)
            cid = (f_acr, rel.id.pre, rel.id.core, rel.id.suf)
            if f_acr == "" or cid in mem:
                continue
            mem.add(cid)
            if add:
                self.__add_relation_ccno(cid, si_id)
            else:
                self.__delete_relation_ccno(cid, si_id)

    def __update_cache(self, upd: UpdateResults, /) -> None:
        self.__add_si_id(upd.si_id)
        self.culture_ccno[upd.cid] = StrainCultureId(c=upd.si_cu, s=upd.si_id)
        self.__add_del_relations(upd.si_id, upd.del_relations, False)
        self.__add_del_relations(upd.si_id, upd.add_relations, True)

    def update_cache(self, upd: UpdateResults, /) -> None:
        if upd.si_cu > 0 and upd.si_id > 0 and upd.used_in_update:
            self.__update_cache(upd)
        if upd.si_cu < 1 or upd.si_id < 1:
            warnings.warn(
                "[CA-UPD] received malformed IDs "
                + f"[{upd.cid}: SI-CU {upd.si_cu} - SI-ID {upd.si_id}]",
                StrainMatchWarn,
                stacklevel=2,
            )
