from dataclasses import dataclass, field
from typing import Protocol, Self, final


@final
@dataclass(slots=True, kw_only=True)
class HistoryDeposition:
    cc_ids: set[int] = field(default_factory=set)
    designation: tuple[str, str, str] | None = None
    full_designation: str = ""

    def compare(self, deposition: Self | None, /) -> bool:
        if deposition is None:
            return True
        return len(self.cc_ids & deposition.cc_ids) > 0


class _ManagerP(Protocol):
    def get_syn_eq_struct(self, designation: str) -> tuple[str, str, str]: ...


@final
@dataclass(slots=True, kw_only=True)
class HistoryDepositor:
    first: HistoryDeposition | None = None
    second: HistoryDeposition | None = None
    counter: int = 0

    def __get_fallback_designation(self) -> str:
        if self.second is None:
            return ""
        return self.second.full_designation

    def deposition_designation(self, out_src: str, manager: _ManagerP, /) -> str:
        results: str = ""
        if self.first is None:
            results = self.__get_fallback_designation()
        else:
            results = self.first.full_designation
        eq_res = manager.get_syn_eq_struct(results)
        if (
            eq_res[0] != ""
            and eq_res[1] != ""
            and manager.get_syn_eq_struct(out_src) == eq_res
        ):
            return ""
        return results

    def add_depositor(self, dep: HistoryDeposition | None, /) -> bool:
        if dep is not None and self.counter < 2:
            if self.counter == 0:
                self.first = dep
            elif self.counter == 1:
                self.second = dep
            self.counter += 1
        return self.counter >= 2

    def is_compatible_deposition(self, depositor: Self | None, /) -> bool:
        if depositor is None:
            return True
        if self.first is not None and _compare_depositor(self.first, depositor):
            return True
        if self.second is not None and _compare_depositor(self.second, depositor):
            return True
        return self.second is None and self.first is None


def _compare_depositor(
    deposition: HistoryDeposition, depositor: HistoryDepositor, /
) -> bool:
    if deposition.compare(depositor.first):
        return True
    if deposition.compare(depositor.second):
        return True
    return False


@final
@dataclass(slots=True, kw_only=True)
class DepositCon:
    designation: str
    history: list[str]
    deposited_as: int
    cc_id: int
    rel_des: list[str]
