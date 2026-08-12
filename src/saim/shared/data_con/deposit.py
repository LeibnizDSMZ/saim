from datetime import datetime
from enum import Enum
import json
from typing import Annotated, Any, Final, Self, final
import unicodedata

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    PlainSerializer,
    model_validator,
)

from saim.shared.data_con.plugins.sample import Sample
from saim.designation.manager import AcronymManager
from saim.shared.data_con.plugins.dep_iso import Deposition, Isolation, Registration
from saim.shared.data_con.taxon import DomainKnownL
from saim.shared.parse.general import pa_int, pa_str
from saim.shared.parse.sequence import check_sequence
from saim.shared.parse.doi import check_doi
from saim.shared.parse.string import (
    clean_edges,
    clean_id_edges,
    clean_text_rm_tags,
    trim_edges,
)
from saim.shared.data_con.designation import CCNoIdM
from saim.shared.data_con.strain import StrainCCNo
from saim.shared.data_ops.clean import detect_empty_dict_keys
from saim.shared.parse.date import check_date_str, date_to_str
from saim.shared.parse.taxa import fix_taxa_name
from saim.taxon_name.manager import TaxonManager

_REQ_KEYS_DEP: Final[tuple[str, ...]] = (
    "registration",
    "domain",
    "designation",
)
_REQ_KEYS_DEP_CCNO: Final[tuple[str, ...]] = (
    "acronym",
    "id",
    "collectionId",
    "ccno",
    "typeStrain",
    "status",
    "source",
)


@final
class DepositStatus(str, Enum):
    # not available
    pri = "private"
    dea = "dead"
    # available
    ava = "available"
    # err
    err = "erroneous data"


@final
class DCDSrc(str, Enum):
    str = "straininfo archive"
    db_e = "external database"
    db_m = "mirri database"
    brc_s = "scraped from brc website"
    brc_v = "found on brc website"
    brc_r = "provided by brc"


def get_dep_sta_enum() -> list[str]:
    return [str(sta.value) for sta in DepositStatus]


_L_STA: Final[set[str]] = {str(sta.value) for sta in DepositStatus}
_DEP_STA: Final[list[str]] = [str(DepositStatus.err.value)]


def is_dep_status(name: str, /) -> bool:
    return name in _L_STA


def get_dep_err_states() -> list[str]:
    return _DEP_STA


def is_dep_erroneous(name: str, /) -> bool:
    return name in _DEP_STA


def get_id_src_enum() -> list[str]:
    return [str(src.value) for src in DCDSrc]


_L_SRC: Final[set[str]] = {str(src.value) for src in DCDSrc}


def is_id_source(name: str, /) -> bool:
    return name in _L_SRC


class _DepCore(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_default=False)

    # optional fields - default
    deposit_id: Annotated[int | None, BeforeValidator(pa_int), Field(ge=1)] = Field(
        default=None, alias="depositId"
    )
    strain: StrainCCNo = Field(default_factory=StrainCCNo)
    sample: Sample = Field(default_factory=Sample)
    isolation: Isolation = Field(default_factory=Isolation)
    taxon_name: Annotated[
        str | None, AfterValidator(fix_taxa_name), Field(min_length=2)
    ] = Field(default=None, alias="taxonName")
    sequence: list[Annotated[str, AfterValidator(check_sequence)]] = Field(
        default_factory=list, alias="sequenceAccessionNumber"
    )
    literature: list[Annotated[str, AfterValidator(check_doi)]] = Field(
        default_factory=list, alias="literatureDOI"
    )

    def patch_taxon_name(self, tax_man: TaxonManager | None = None, /) -> None:
        if tax_man is not None and self.taxon_name is not None:
            self.taxon_name = tax_man.get_patched_name(self.taxon_name)

    def to_dict_main(
        self,
        trim: bool = True,
        /,
    ) -> dict[str, Any]:
        dict_res = self.model_dump(
            mode="python",
            include={
                "depositId",
                "taxonName",
            },
            by_alias=True,
        )
        dict_res["strain"] = self.strain.to_dict(trim)
        dict_res["sample"] = self.sample.to_dict(trim)
        dict_res["isolation"] = self.isolation.to_dict(trim)
        dict_res["sequenceAccessionNumber"] = list(set(self.sequence))
        dict_res["literatureDOI"] = list(set(self.literature))
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res


@final
class Deposit(_DepCore):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_default=False)

    # required fields - init
    designation: Annotated[str, BeforeValidator(clean_id_edges), Field(min_length=2)]
    domain: DomainKnownL

    registration: Registration

    @model_validator(mode="after")
    def _check_sample(self) -> Self:
        if self.sample.source is None:
            raise ValueError("sample, source - Source required")
        if self.sample.date is None:
            raise ValueError("sample, date - Date required")
        return self

    def to_dict(
        self,
        tax_man: TaxonManager | None = None,
        trim: bool = True,
        /,
    ) -> dict[str, Any]:
        run_deposit_patch_check(self, tax_man)
        dict_res = {
            **super().to_dict_main(trim),
            **self.model_dump(
                mode="python",
                include={"designation"},
                by_alias=True,
            ),
        }
        dict_res["registration"] = self.registration.to_dict(trim)
        dict_res["domain"] = self.domain.value
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                if key not in _REQ_KEYS_DEP:
                    del dict_res[key]
        return dict_res

    def to_json(
        self,
        tax_man: TaxonManager | None = None,
        /,
    ) -> str:
        return unicodedata.normalize(
            "NFKD", json.dumps(self.to_dict(tax_man, True), ensure_ascii=False)
        )


@final
class DepositCCNo(_DepCore):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_default=False)

    # required fields - init
    type_strain: bool = Field(alias="typeStrain")
    id: CCNoIdM
    acr: Annotated[str, BeforeValidator(clean_edges), Field(min_length=2)] = Field(
        alias="acronym"
    )
    brc_id: Annotated[int, Field(ge=1)] = Field(alias="collectionId")
    ccno: Annotated[str, BeforeValidator(clean_id_edges), Field(min_length=2)]
    source: DCDSrc

    # optional fields - default
    domain: DomainKnownL | None = None
    status: DepositStatus | None = None
    url: Annotated[
        HttpUrl | None,
        BeforeValidator(trim_edges),
        PlainSerializer(lambda val: str(val), return_type=str),
    ] = None
    history: Annotated[
        str | None, BeforeValidator(clean_text_rm_tags), Field(min_length=2)
    ] = None
    parent: Annotated[str | None, BeforeValidator(trim_edges), Field(min_length=3)] = (
        Field(default=None, alias="parentDesignation")
    )
    deposition: Deposition = Field(default_factory=Deposition)
    # resource acquired date
    update: Annotated[
        str, BeforeValidator(trim_edges), AfterValidator(check_date_str)
    ] = Field(default_factory=lambda: date_to_str(datetime.now(), True))

    def __check_known_acr(self, acr_man: AcronymManager, /) -> None:
        if self.brc_id not in acr_man.identify_acr(self.acr):
            raise ValueError(f"mismatch brc_id - {self.ccno} | {self.brc_id}")
        kn_acr = acr_man.identify_ccno_by_brc(self.ccno, self.brc_id)
        if kn_acr.acr == "":
            raise ValueError(f"could not detect acronym - {self.acr} | {self.brc_id}")
        if kn_acr.acr.lower() != self.acr.lower():
            raise ValueError(f"mismatch acronym - {self.acr} | {kn_acr.acr}")
        if kn_acr.id.pre.lower() != pa_str(self.id.pre).lower():
            raise ValueError(f"mismatch id prefix - {self.id.pre} | {kn_acr.id.pre}")
        if kn_acr.id.core.lower() != pa_str(self.id.core).lower():
            raise ValueError(f"mismatch id core - {self.id.core} | {kn_acr.id.core}")
        if kn_acr.id.suf.lower() != pa_str(self.id.suf).lower():
            raise ValueError(f"mismatch id suffix - {self.id.suf} | {kn_acr.id.suf}")

    def check_known_acr(self, acr_man: AcronymManager | None, /) -> None:
        if acr_man is not None:
            self.__check_known_acr(acr_man)

    @model_validator(mode="after")
    def _check_culture_ids_completeness(self) -> Self:
        if self.acr.lower() not in self.ccno.lower():
            raise ValueError(
                f"acr, ccno - acronym not in CCNo - {self.ccno} | {self.acr}"
            )
        if self.id.full is None or self.id.full.lower() not in self.ccno.lower():
            raise ValueError(f"id, ccno - id not in CCNo - {self.ccno} | {self.id.full}")
        return self

    def patch_strain(self) -> None:
        self.strain.patch_relation(self.acr, self.id.to_ccno_id())

    def to_dict_min(self) -> dict[str, Any]:
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
            if key not in _REQ_KEYS_DEP_CCNO:
                del dict_res[key]
        return dict_res

    def to_dict(
        self,
        tax_man: TaxonManager | None = None,
        acr_man: AcronymManager | None = None,
        trim: bool = True,
        /,
    ) -> dict[str, Any]:
        run_ccno_patch_check(self, tax_man, acr_man)
        dict_res = {
            **super().to_dict_main(trim),
            **self.model_dump(
                mode="python",
                include={
                    "acr",
                    "brc_id",
                    "ccno",
                    "type_strain",
                    "domain",
                    "source",
                    "history",
                    "parent",
                    "update",
                },
                by_alias=True,
            ),
        }
        dict_res["id"] = self.id.to_dict(trim)
        dict_res["deposition"] = self.deposition.to_dict(trim)
        if self.url is not None:
            dict_res["url"] = self.url.encoded_string()
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                if key not in _REQ_KEYS_DEP_CCNO:
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


def run_ccno_patch_check(
    con: DepositCCNo, tax_man: TaxonManager | None, acr_man: AcronymManager | None, /
) -> None:
    con.check_known_acr(acr_man)
    con.patch_taxon_name(tax_man)
    con.patch_strain()


def run_deposit_patch_check(con: Deposit, tax_man: TaxonManager | None, /) -> None:
    con.patch_taxon_name(tax_man)
