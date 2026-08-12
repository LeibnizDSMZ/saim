from typing import Protocol


class _PerInf(Protocol):
    @property
    def orcid(self) -> str | None: ...
    @property
    def name(self) -> str | None: ...


def ch_person_info(per: _PerInf) -> _PerInf:
    if not per.orcid or not per.name:
        raise ValueError("ORCID and Name must be provided!")
    return per
