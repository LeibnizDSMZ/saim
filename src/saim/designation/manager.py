from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Self, final

from saim.designation.extract_ccno import (
    extract_ccno_from_text,
    identify_all_valid_ccno,
    identify_ccno,
    identify_designation_type,
    identify_designation_types,
)
from saim.designation.known_acr_db import create_brc_con, identify_acr
from saim.shared.data_con.designation import CCNoDes, CCNoId, DesignationType
from cafi.container.acr_db import AcrDbEntry
from saim.shared.data_con.brc import BrcContainer


def _verify_date[T, V](
    func: Callable[["AcronymManager", V], T],
) -> Callable[["AcronymManager", V], T]:
    def wrap(self: "AcronymManager", arg: V) -> T:
        if datetime.now() - timedelta(days=self._exp_days) > self._start:
            self._ca_req = {}
            self._ca_req_all = {}
            self._ca_brc = create_brc_con(self.version)
        return func(self, arg)

    return wrap


def _cr_ccno_des(val: tuple[str, str, str, str, str, str], /) -> CCNoDes:
    des, acr, ful, pre, core, suf = val
    return CCNoDes(
        designation=des, acr=acr, id=CCNoId(full=ful, core=core, pre=pre, suf=suf)
    )


def _cr_tuple_from_ccno_des(ccno_des: CCNoDes, /) -> tuple[str, str, str, str, str, str]:
    return (
        ccno_des.designation,
        ccno_des.acr,
        ccno_des.id.full,
        ccno_des.id.pre,
        ccno_des.id.core,
        ccno_des.id.suf,
    )


@final
class AcronymManager:
    __slots__ = (
        "__limit",
        "__version",
        "_ca_brc",
        "_ca_req",
        "_ca_req_all",
        "_exp_days",
        "_start",
    )
    __instance: Self | None = None

    def __init__(
        self,
        version: str,
        limit: int = 1_000,
        /,
    ) -> None:
        self.__version = version
        self._exp_days = 60
        self._start = datetime.now()
        self._ca_brc = create_brc_con(self.version)
        self._ca_req: dict[str, tuple[str, str, str, str, str, str]] = {}
        self._ca_req_all: dict[str, list[tuple[str, str, str, str, str, str]]] = {}
        self.__limit = limit
        super().__init__()

    def __new__(cls, *_args: Path | str) -> Self:
        if cls.__instance is not None:
            return cls.__instance
        cls.__instance = super().__new__(cls)
        return cls.__instance

    def get_brc_by_id(self, brc_id: int, /) -> AcrDbEntry | None:
        return self._ca_brc.cc_db.get(brc_id, None)

    @property
    def brc_container(self) -> BrcContainer:
        return self._ca_brc

    @property
    def version(self) -> str:
        return self.__version

    def __check_limit(self) -> None:
        if len(self._ca_req) > self.__limit:
            key = next(iter(self._ca_req))
            self._ca_req.pop(key)
        if len(self._ca_req_all) > self.__limit:
            key = next(iter(self._ca_req_all))
            self._ca_req_all.pop(key)

    @_verify_date
    def identify_ccno(self, designation: str, /) -> CCNoDes:
        trimmed = designation.strip()
        if trimmed in self._ca_req_all and trimmed in self._ca_req:
            del self._ca_req[trimmed]
        if trimmed in self._ca_req_all and len(self._ca_req_all[trimmed]) > 0:
            return _cr_ccno_des(self._ca_req_all[trimmed][0])
        if trimmed in self._ca_req:
            return _cr_ccno_des(self._ca_req[trimmed])
        ide = identify_ccno(designation, self._ca_brc)
        self.__check_limit()
        self._ca_req[trimmed] = _cr_tuple_from_ccno_des(ide)
        return ide

    def identify_ccno_by_brc(self, designation: str, brc_id: int, /) -> CCNoDes:
        for ccno in self.identify_ccno_all_valid(designation):
            if ccno.acr != "" and brc_id in self.identify_acr(ccno.acr):
                return ccno
        return CCNoDes(designation=designation)

    @_verify_date
    def identify_ccno_all_valid(self, designation: str, /) -> list[CCNoDes]:
        trimmed = designation.strip()
        if trimmed in self._ca_req_all:
            return [_cr_ccno_des(val) for val in self._ca_req_all[trimmed]]
        ides = identify_all_valid_ccno(designation, self._ca_brc)
        if len(ides) > 0:
            self.__check_limit()
            self._ca_req_all[trimmed] = [_cr_tuple_from_ccno_des(ide) for ide in ides]
        return ides

    @_verify_date
    def extract_all_valid_ccno_from_text(self, text: str, /) -> Iterable[CCNoDes]:
        yield from extract_ccno_from_text(text, self._ca_brc)

    @_verify_date
    def identify_acr(self, acr: str, /) -> set[int]:
        return identify_acr(acr, self._ca_brc)

    @_verify_date
    def is_brc_deprecated(self, brc_id: int, /) -> bool:
        dep = self._ca_brc.cc_db.get(brc_id, None)
        if dep is None or dep.deprecated:
            return True
        return False

    def identify_designation_type(self, des: str, /) -> DesignationType:
        return identify_designation_type(self.identify_ccno(des))

    def identify_designation_types(self, des: str, /) -> list[DesignationType]:
        results = set(
            des_type
            for ccno in self.identify_ccno_all_valid(des)
            for des_type in identify_designation_types(ccno)
        )
        results.discard(DesignationType.des)
        if len(results) == 0:
            return [DesignationType.des]
        return list(results)
