from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, final

from saim.shared.data_con.culture import CultureStatus
from saim.shared.data_con.designation import CCNoIdP


class JsonSerCon(Protocol):
    def to_json(self) -> str: ...


class StrainRelation(Protocol):
    @property
    def relation(self) -> list[str]: ...


class CultureMatch(JsonSerCon, Protocol):
    @property
    def ccno(self) -> str: ...
    @property
    def acr(self) -> str: ...
    @property
    def brc_id(self) -> int: ...
    @property
    def id(self) -> CCNoIdP: ...
    @property
    def status(self) -> CultureStatus: ...
    @property
    def strain(self) -> StrainRelation: ...


@final
class ErrType(str, Enum):
    inv_brc = "BRC IS DEPRECATED"
    inv_cul = "CULTURE IS ERRONEOUS"
    err_ca = "BROKEN CACHE - CONTAINS -1 IDS"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ErrCon[IN: JsonSerCon]:
    error: list[ErrType]
    data: IN


@final
@dataclass(slots=True, frozen=True, kw_only=True)
class CulMatCon[IN: JsonSerCon]:
    cul: IN
    culture_id: int = -1
    strain_id: int = -1
    fallback_strain_ids: list[int] = field(default_factory=list)
