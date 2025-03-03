from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Self, final

from saim.designation.extract_ccno import get_syn_eq_struct
from saim.designation.known_acr_db import create_brc_con
from saim.history.private.detect import detect_culture_collections
from saim.history.private.split import split_history, split_history_event
from saim.history.private.types import DESIGNATION, HISTORY, STRAIN_CC
from saim.shared.data_con.brc import BrcContainer
from saim.shared.data_con.history import HistoryDeposition


def _is_not_duplicate(event: HistoryDeposition, cc_id: int, /) -> bool:
    if cc_id in event.cc_ids:
        event.cc_ids.remove(cc_id)
    return len(event.cc_ids) > 0


def _verify_date[
    T, V
](func: Callable[["HistoryManager", V], T]) -> Callable[["HistoryManager", V], T]:
    def wrap(self: "HistoryManager", arg: V) -> T:
        if datetime.now() - timedelta(days=self._exp_days) > self._start:
            self._ca_req = {}
            self._ca_brc = create_brc_con(self.version)
        return func(self, arg)

    return wrap


@final
class HistoryManager:
    __slots__ = (
        "__limit",
        "__version",
        "_ca_brc",
        "_ca_req",
        "_exp_days",
        "_start",
    )
    __instance: Self | None = None

    def __init__(self, version: str, limit: int = 1_000, /) -> None:
        self._exp_days = 60
        self.__version = version
        self._ca_brc = create_brc_con(self.version)
        self._ca_req: dict[str, tuple[str, str, str]] = {}
        self.__limit = limit
        self._start = datetime.now()
        super().__init__()

    def __new__(cls, *_args: Any) -> Self:
        if cls.__instance is not None:
            return cls.__instance
        cls.__instance = super().__new__(cls)
        return cls.__instance

    @property
    def version(self) -> str:
        return self.__version

    @property
    def culture_collection_con(self) -> BrcContainer:
        return self._ca_brc

    def __check_limit(self) -> None:
        if len(self._ca_req) > self.__limit:
            key = next(iter(self._ca_req))
            self._ca_req.pop(key)

    @_verify_date
    def get_syn_eq_struct(self, designation: str, /) -> tuple[str, str, str]:
        trimmed = designation.strip()
        if (equ := self._ca_req.get(trimmed, None)) is not None:
            return equ
        equ = get_syn_eq_struct(trimmed)
        self.__check_limit()
        self._ca_req[trimmed] = equ
        return equ

    def parse_history(
        self, history: str, root_cc_id: int, root_des: DESIGNATION, cc_des: STRAIN_CC, /
    ) -> HISTORY:
        hist = split_history(history)
        results = [
            ana
            for evi, event in enumerate(hist)
            if (
                ana := detect_culture_collections(
                    list(split_history_event(event)), cc_des, self._ca_brc
                )
            )
            is None
            or evi > 0
            or _is_not_duplicate(ana, root_cc_id)
        ]
        results.insert(
            0,
            HistoryDeposition(
                cc_ids={root_cc_id},
                designation=root_des[1:],
                full_designation=root_des[0],
            ),
        )
        return results
