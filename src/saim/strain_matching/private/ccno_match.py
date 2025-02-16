from typing import Protocol, final

from saim.designation.manager import AcronymManager
from saim.shared.data_con.culture import is_cul_erroneous
from saim.shared.data_con.strain import StrainCultureId
from saim.shared.error.exceptions import StrainMatchEx
from saim.strain_matching.private.container import (
    CulMatCon,
    CultureMatch,
    ErrCon,
    ErrType,
)


_CCNO_CACHE = dict[tuple[int, str, str, str], StrainCultureId]


class _CacheProt(Protocol):
    @property
    def si_cu_err(self) -> set[int]: ...
    @property
    def culture_ccno(self) -> _CCNO_CACHE: ...


@final
class CCNoMatch[CT: CultureMatch]:
    __slots__ = ("__ca_brc", "__ca_cul_ccno", "__ca_si_cu_err")

    def __init__(self, cache: _CacheProt, ca_brc: AcronymManager, /) -> None:
        self.__ca_cul_ccno = cache.culture_ccno
        self.__ca_brc = ca_brc
        self.__ca_si_cu_err = cache.si_cu_err
        if -1 in self.__ca_si_cu_err:
            raise StrainMatchEx("-1 was detected inside the banned cid set")
        super().__init__()

    def __is_cul_err(self, cul_up: CulMatCon[CT], /) -> bool:
        if is_cul_erroneous(cul_up.cul.status):
            return True
        return False

    def __err_types(
        self, b_brc: bool, b_cul: bool, err_ca: bool, cid: int, /
    ) -> list[ErrType]:
        err_types = []
        if err_ca:
            err_types.append(ErrType.err_ca)
        if b_brc:
            err_types.append(ErrType.inv_brc)
        if b_cul or cid in self.__ca_si_cu_err:
            err_types.append(ErrType.inv_cul)
        return err_types

    def __validate_ccno(self, cul_up: CulMatCon[CT], /) -> ErrCon[CT] | CulMatCon[CT]:
        b_brc = self.__ca_brc.is_brc_deprecated(cul_up.cul.brc_id)
        b_cul = self.__is_cul_err(cul_up)
        err_ca = cul_up.culture_id != cul_up.strain_id and cul_up.culture_id < 1
        err_cul = b_brc or b_cul or cul_up.culture_id in self.__ca_si_cu_err
        if err_ca or err_cul:
            return ErrCon(
                error=self.__err_types(b_brc, b_cul, err_ca, cul_up.culture_id),
                data=cul_up.cul,
            )
        return cul_up

    def __find_ccno(self, cul: CT, /) -> CulMatCon[CT]:
        cid = (cul.brc_id, cul.id.pre, cul.id.core, cul.id.suf)
        if (mat := self.__ca_cul_ccno.get(cid, None)) is not None:
            return CulMatCon(
                cul=cul,
                culture_id=mat.c,
                strain_id=mat.s,
            )
        return CulMatCon(cul=cul)

    def match(self, cul: CT, /) -> ErrCon[CT] | CulMatCon[CT]:
        return self.__validate_ccno(self.__find_ccno(cul))
