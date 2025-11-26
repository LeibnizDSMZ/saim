from datetime import datetime
from enum import Enum
import json
from typing import Annotated, Any, Final, final
import unicodedata

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    PlainSerializer,
    model_validator,
)

from saim.shared.data_con.plugins.sample import Sample
from saim.designation.manager import AcronymManager
from saim.shared.data_con.plugins.dep_iso import Deposition, Isolation
from saim.shared.parse.sequence import check_sequence
from saim.shared.parse.string import (
    clean_edges,
    clean_id_edges,
    clean_ledge_rm_tags,
    clean_text_rm_tags,
    trim_edges,
)
from saim.shared.data_con.designation import CCNoIdM
from saim.shared.data_con.strain import StrainCCNo
from saim.shared.data_ops.clean import detect_empty_dict_keys
from saim.shared.parse.date import check_date_str, date_to_str
from saim.taxon_name.manager import TaxonManager

_REQ_KEYS: Final[tuple[str, ...]] = (
    "acronym",
    "id",
    "collectionId",
    "ccno",
    "typeStrain",
    "status",
    "source",
)


@final
class CultureStatus(str, Enum):
    # not available
    pri = "private"
    dea = "dead"
    unk = "unknown"
    # available
    ava = "available"
    # err
    err = "erroneous data"


@final
class CiDSrc(str, Enum):
    str = "straininfo archive"
    db_e = "external database"
    db_m = "mirri database"
    brc_s = "scraped from brc website"
    brc_v = "found on brc website"
    brc_r = "provided by brc"


def get_cul_sta_enum() -> list[str]:
    return [str(sta.value) for sta in CultureStatus]


_L_STA: Final[set[str]] = {str(sta.value) for sta in CultureStatus}
_DEP_STA: Final[list[str]] = [str(CultureStatus.err.value)]


def is_cul_status(name: str, /) -> bool:
    return name in _L_STA


def get_cul_err_states() -> list[str]:
    return _DEP_STA


def is_cul_erroneous(name: str, /) -> bool:
    return name in _DEP_STA


def get_id_src_enum() -> list[str]:
    return [str(src.value) for src in CiDSrc]


_L_SRC: Final[set[str]] = {str(src.value) for src in CiDSrc}


def is_id_source(name: str, /) -> bool:
    return name in _L_SRC


def _fix_name(source: Any) -> str:
    if not isinstance(source, str):
        return ""
    clean = clean_ledge_rm_tags(source)
    if len(clean) > 1:
        return clean[0].upper() + clean[1:]
    return clean


@final
class CultureCCNo(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_default=False)
    _strict: bool

    # required fields - init
    id: CCNoIdM
    acr: Annotated[str, AfterValidator(clean_edges), Field(min_length=2)] = Field(
        alias="acronym"
    )
    brc_id: Annotated[int, Field(ge=1)] = Field(alias="collectionId")
    ccno: Annotated[str, AfterValidator(clean_id_edges), Field(min_length=2)]
    status: CultureStatus
    type_strain: bool = Field(alias="typeStrain")
    source: CiDSrc
    # optional fields - default
    url: (
        Annotated[HttpUrl, PlainSerializer(lambda val: str(val), return_type=str)] | None
    ) = None
    cul_id: Annotated[int, Field(ge=1)] | None = Field(default=None, alias="cultureId")
    history: Annotated[str, AfterValidator(clean_text_rm_tags), Field(min_length=2)] = ""
    parent: Annotated[str, AfterValidator(trim_edges), Field(min_length=3)] = Field(
        default="", alias="parentDesignation"
    )
    strain: StrainCCNo = Field(default_factory=StrainCCNo)
    sample: Sample = Field(default_factory=Sample)
    isolation: Isolation = Field(default_factory=Isolation)
    deposition: Deposition = Field(default_factory=Deposition)
    taxon_name: Annotated[str, AfterValidator(_fix_name), Field(min_length=4)] = Field(
        default="", alias="taxonName"
    )
    sequence: list[Annotated[str, AfterValidator(check_sequence)]] = Field(
        default_factory=list, alias="sequenceAccessionNumber"
    )
    # resource acquired date
    update: Annotated[str, AfterValidator(trim_edges), AfterValidator(check_date_str)] = (
        Field(default_factory=lambda: date_to_str(datetime.now(), True))
    )

    def __init__(self, *, mode: bool = False, **data: dict[str, Any]) -> None:
        super().__init__(**data)
        self._strict = mode

    def __check_known_acr(self, acr_man: AcronymManager, /) -> None:
        if self.brc_id not in acr_man.identify_acr(self.acr):
            raise ValueError(f"mismatch brc_id - {self.ccno} | {self.brc_id}")
        kn_acr = acr_man.identify_ccno_by_brc(self.ccno, self.brc_id)
        if kn_acr.acr.lower() != self.acr.lower():
            raise ValueError(f"mismatch acronym - {self.acr} | {kn_acr.acr}")
        if kn_acr.id.pre.lower() != self.id.pre.lower():
            raise ValueError(f"mismatch id prefix - {self.id.pre} | {kn_acr.id.pre}")
        if kn_acr.id.core.lower() != self.id.core.lower():
            raise ValueError(f"mismatch id core - {self.id.core} | {kn_acr.id.core}")
        if kn_acr.id.suf.lower() != self.id.suf.lower():
            raise ValueError(f"mismatch id suffix - {self.id.suf} | {kn_acr.id.suf}")

    def check_known_acr(self, acr_man: AcronymManager | None, /) -> None:
        if acr_man is not None:
            self.__check_known_acr(acr_man)

    @model_validator(mode="after")
    def check_culture_ids_completeness(self) -> "CultureCCNo":
        if self.acr.lower() not in self.ccno.lower():
            raise ValueError(f"acronym not in CCNo - {self.ccno} | {self.acr}")
        if self.id.full.lower() not in self.ccno.lower():
            raise ValueError(f"id not in CCNo - {self.ccno} | {self.id.full}")
        return self

    def patch_taxon_name(self, tax_man: TaxonManager | None = None, /) -> None:
        if tax_man is not None:
            self.taxon_name = tax_man.get_patched_name(self.taxon_name)

    def patch_strain(self) -> None:
        self.strain.patch_relation(self.acr, self.id)

    def to_dict_core(self) -> dict[str, Any]:
        dict_res = self.model_dump(
            mode="python",
            include={
                "acr",
                "brc_id",
                "ccno",
                "type_strain",
                "source",
                "update",
                "status",
            },
            by_alias=True,
        )
        dict_res["id"] = self.id.to_dict(True)
        for key in detect_empty_dict_keys(dict_res):
            if key not in _REQ_KEYS:
                del dict_res[key]
        return dict_res

    def to_dict(
        self,
        tax_man: TaxonManager | None = None,
        acr_man: AcronymManager | None = None,
        trim: bool = True,
        /,
    ) -> dict[str, Any]:
        run_patch_check(self, tax_man, acr_man)
        dict_res = self.model_dump(
            mode="python",
            exclude={
                "id",
                "id_syn",
                "strain",
                "sample",
                "isolation",
                "deposition",
                "seq",
            },
            by_alias=True,
        )
        # is not saved
        dict_res["id"] = self.id.to_dict(trim)
        # case sensitivity to vague for being a synonym
        dict_res["strain"] = self.strain.to_dict(trim)
        dict_res["sample"] = self.sample.to_dict(trim)
        dict_res["isolation"] = self.isolation.to_dict(trim)
        dict_res["deposition"] = self.deposition.to_dict(trim)
        dict_res["sequenceAccessionNumber"] = list(set(self.sequence))
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                if key not in _REQ_KEYS:
                    del dict_res[key]
        return dict_res

    def to_json(
        self,
        tax_man: TaxonManager | None = None,
        acr_man: AcronymManager | None = None,
        /,
    ) -> str:
        return unicodedata.normalize(
            "NFKD", json.dumps(self.to_dict(tax_man, acr_man, True), ensure_ascii=False)
        )


def run_patch_check(
    con: CultureCCNo, tax_man: TaxonManager | None, acr_man: AcronymManager | None, /
) -> None:
    con.check_known_acr(acr_man)
    con.patch_taxon_name(tax_man)
    con.patch_strain()
