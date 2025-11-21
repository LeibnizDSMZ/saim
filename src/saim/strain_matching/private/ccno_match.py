from typing import Protocol, final

from saim.designation.manager import AcronymManager
from saim.shared.data_con.deposit import is_dep_erroneous
from saim.shared.data_con.strain import StrainDepositId
from saim.shared.error.exceptions import StrainMatchEx
from saim.strain_matching.private.container import (
    DepMatCon,
    DepositMatch,
    ErrCon,
    ErrType,
)


_CCNO_CACHE = dict[tuple[int, str, str, str], StrainDepositId]


class _CacheProt(Protocol):
    @property
    def si_dp_err(self) -> set[int]: ...
    @property
    def deposit_ccno(self) -> _CCNO_CACHE: ...


@final
class CCNoMatch[CT: DepositMatch]:
    __slots__ = ("__ca_brc", "__ca_dep_ccno", "__ca_si_dp_err")

    def __init__(self, cache: _CacheProt, ca_brc: AcronymManager, /) -> None:
        self.__ca_dep_ccno = cache.deposit_ccno
        self.__ca_brc = ca_brc
        self.__ca_si_dp_err = cache.si_dp_err
        if -1 in self.__ca_si_dp_err:
            raise StrainMatchEx("-1 was detected inside the banned cid set")
        super().__init__()

    def __is_dep_err(self, dep_up: DepMatCon[CT], /) -> bool:
        if is_dep_erroneous(dep_up.dep.status):
            return True
        return False

    def __err_types(
        self, b_brc: bool, b_dep: bool, err_ca: bool, cid: int, /
    ) -> list[ErrType]:
        err_types = []
        if err_ca:
            err_types.append(ErrType.err_ca)
        if b_brc:
            err_types.append(ErrType.inv_brc)
        if b_dep or cid in self.__ca_si_dp_err:
            err_types.append(ErrType.inv_dep)
        return err_types

    def __validate_ccno(self, dep_up: DepMatCon[CT], /) -> ErrCon[CT] | DepMatCon[CT]:
        b_brc = self.__ca_brc.is_brc_deprecated(dep_up.dep.brc_id)
        b_dep = self.__is_dep_err(dep_up)
        err_ca = dep_up.deposit_id != dep_up.strain_id and dep_up.deposit_id < 1
        err_dep = b_brc or b_dep or dep_up.deposit_id in self.__ca_si_dp_err
        if err_ca or err_dep:
            return ErrCon(
                error=self.__err_types(b_brc, b_dep, err_ca, dep_up.deposit_id),
                data=dep_up.dep,
            )
        return dep_up

    def __find_ccno(self, dep: CT, /) -> DepMatCon[CT]:
        cid = (dep.brc_id, dep.id.pre, dep.id.core, dep.id.suf)
        if (mat := self.__ca_dep_ccno.get(cid, None)) is not None:
            return DepMatCon(
                dep=dep,
                deposit_id=mat.c,
                strain_id=mat.s,
            )
        return DepMatCon(dep=dep)

    def match(self, dep: CT, /) -> ErrCon[CT] | DepMatCon[CT]:
        return self.__validate_ccno(self.__find_ccno(dep))
