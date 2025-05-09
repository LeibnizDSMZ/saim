from dataclasses import dataclass, field
from typing import final

from cafi.container.acr_db import AcrDbEntry
from saim.shared.search.radix_tree import RadixTree


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AcrDbEntryFixed:
    f_acr_syn: set[str] = field(default_factory=set)
    f_acr: str = ""
    f_code: str = ""


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BrcContainer:
    cc_db: dict[int, AcrDbEntry]
    f_cc_db: dict[int, AcrDbEntryFixed]
    f_cc_db_acr: dict[str, set[int]]
    f_cc_db_code: dict[str, set[int]]
    kn_acr: RadixTree[None]
    kn_acr_rev: RadixTree[None]
