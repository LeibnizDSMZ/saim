from dataclasses import dataclass, field
from typing import Annotated, Any, final

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from saim.shared.data_con.taxon import DomainE, parse_gbif_rank, GBIFRanksE, GBIFTypeE


def _check_rank(rank: Any, /) -> GBIFRanksE:
    if not isinstance(rank, str):
        raise ValueError("Rank {rank} is not a string")  # noqa: TRY004
    return parse_gbif_rank(rank)


@final
@dataclass(slots=True, kw_only=True, frozen=True)
class GBIF:
    name: str = ""
    rank_marker: GBIFRanksE = GBIFRanksE.oth


@final
class GBIFName(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", validate_default=False)

    type: GBIFTypeE
    parsed: bool
    parsed_par: bool = Field(alias="parsedPartially")
    sci_name: str = Field(alias="scientificName")
    # optional
    rank: Annotated[GBIFRanksE, BeforeValidator(_check_rank)] = Field(
        default=GBIFRanksE.oth, alias="rankMarker"
    )
    canon_mark: str = Field(default="", alias="canonicalNameWithMarker")
    genus: str = Field(default="", alias="genusOrAbove")


@final
class LpsnOrgC(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", validate_default=False)

    id: int
    full_name: Annotated[str, Field(min_length=1)]
    category: Annotated[str, Field(min_length=1)]
    lpsn_correct_name_id: int | None = None
    lpsn_parent_id: int | None = None
    type_strain_names: list[Annotated[str, Field(min_length=1)]] = Field(
        default_factory=list
    )


@final
class LPSNName(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", validate_default=False)

    next: Annotated[str, Field(min_length=1)] | None
    results: list[int]


@final
class LPSNId(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", validate_default=False)

    next: Annotated[str, Field(min_length=1)] | None
    results: list[LpsnOrgC]


@final
class NcbiTaxCon(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", validate_default=False)

    name: dict[Annotated[str, Field(min_length=1)], set[int]]
    id_2_name: dict[int, Annotated[str, Field(min_length=1)]]
    eq_name: dict[Annotated[str, Field(min_length=1)], set[int]]
    synonyms: dict[Annotated[str, Field(min_length=1)], set[int]]
    type_str: dict[int, set[Annotated[str, Field(min_length=1)]]]
    rank: dict[int, GBIFRanksE]
    domain: dict[int, int]
    kingdom: dict[int, int]
    genus: dict[int, int]
    species: dict[int, int]
    map_ids: dict[int, int]
    rm_ids: set[int]


@dataclass(frozen=True, kw_only=True, slots=True)
class _IdCon:
    ncbi: set[int] = field(default_factory=set)
    lpsn: set[int] = field(default_factory=set)


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class CorTaxonNameId(_IdCon):
    name: str


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class RankId(_IdCon):
    rank: GBIFRanksE


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class DomainId(_IdCon):
    domain: DomainE


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class GenusId(_IdCon):
    genus: str


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class SpeciesId(_IdCon):
    species: str


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class LPSNConf:
    user: str
    pw: str
    url: str


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class TaxonName:
    name: str
    ncbi: int = -1
    lpsn: int = -1


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class TaxonOV:
    species: bool = False
    genus: bool = False
    domain: bool = False
    fail: bool = False
