from enum import Enum
import re
from typing import Annotated, Final, Protocol, final
from dataclasses import asdict, dataclass, field

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator
from saim.shared.parse.string import (
    clean_core_id_edges,
    clean_id_edges,
    trim_edges,
)
from saim.shared.data_ops.clean import detect_empty_dict_keys


@final
class DesignationType(str, Enum):
    des = "DESIGNATION"
    ccno = "CCNO"
    mir = "MIRRI"
    wdcm_ref = "WDCM_REF"
    strid = "STRAIN_INFO_SI_ID"
    culid = "STRAIN_INFO_SI_DP"


WDCM_REG: Final[tuple[re.Pattern[str], ...]] = (re.compile(r"^WDCM\s*\d+$"),)
MIRRI_REG: Final[tuple[re.Pattern[str], ...]] = (re.compile(r"^MIRRI\s*\d+$"),)
STRAIN_SI_ID_DOI: Final[re.Pattern[str]] = re.compile(
    r"^(?:.+/)?10.60712/SI-ID\s*(\d+)\.(\d+)$"
)
STRAIN_INFO_SI_ID_REG: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^SI-ID\s*(\d+)(?:\.(\d+))?$"),
    STRAIN_SI_ID_DOI,
)
STRAIN_INFO_SI_CU_REG: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^SI-CU\s*(\d+)$"),
)

ALL_DES_TYPES: Final[tuple[tuple[DesignationType, tuple[re.Pattern[str], ...]], ...]] = (
    (DesignationType.wdcm_ref, WDCM_REG),
    (DesignationType.mir, MIRRI_REG),
    (DesignationType.strid, STRAIN_INFO_SI_ID_REG),
    (DesignationType.culid, STRAIN_INFO_SI_CU_REG),
)


class CCNoIdP(Protocol):
    @property
    def full(self) -> str: ...
    @property
    def core(self) -> str: ...
    @property
    def pre(self) -> str: ...
    @property
    def suf(self) -> str: ...


class CCNoDesP(Protocol):
    @property
    def acr(self) -> str: ...
    @property
    def id(self) -> CCNoIdP: ...
    @property
    def designation(self) -> str: ...


@final
@dataclass(slots=True, kw_only=True)
class CCNoId:
    full: str = ""
    core: str = ""
    pre: str = ""
    suf: str = ""


@final
@dataclass(slots=True, kw_only=True)
class CCNoDes:
    acr: str = ""
    id: CCNoId = field(default_factory=CCNoId)
    designation: str = ""


@final
class CCNoIdM(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    full: Annotated[
        str, AfterValidator(clean_id_edges), Field(min_length=1, max_length=32)
    ] = Field(default="")
    core: Annotated[str, AfterValidator(clean_core_id_edges), Field(min_length=1)] = (
        Field(default="")
    )
    pre: Annotated[str, AfterValidator(trim_edges)] = Field(default="")
    suf: Annotated[str, AfterValidator(trim_edges)] = Field(default="")

    def to_dict(self, trim: bool = True, /) -> dict[str, str]:
        return ccno_id_to_dict(self, trim)

    @model_validator(mode="after")
    def _check_culture_ids_completeness(self) -> "CCNoIdM":
        if self.full == "" or self.core == "":
            raise ValueError("empty CCNoId detected")
        if self.core not in self.full:
            raise ValueError("malformed core in CCNoId")
        if self.pre not in self.full:
            raise ValueError("malformed pre in CCNoId")
        if self.suf not in self.full:
            raise ValueError("malformed suf in CCNoId")
        return self


def ccno_id_to_dict(ccno_id: CCNoId | CCNoIdM, trim: bool = True, /) -> dict[str, str]:
    id_dict: dict[str, str] = {}
    if (trim and ccno_id.core == "") or ccno_id.full == "":
        return id_dict
    if isinstance(ccno_id, CCNoIdM):
        id_dict = ccno_id.model_dump(mode="python", by_alias=True)
    else:
        id_dict = asdict(ccno_id)
    if trim:
        for key in detect_empty_dict_keys(id_dict):
            del id_dict[key]
    return id_dict


def ccno_designation_to_dict(
    ccno_des: CCNoDes, trim: bool = True, /
) -> dict[str, str | dict[str, str]]:
    res_dict: dict[str, str | dict[str, str]] = {}
    if (trim and ccno_des.designation == "") or (0 < len(ccno_des.designation) < 3):
        return res_dict
    if ccno_des.id.core == "" or ccno_des.id.full == "":
        ccno_des.acr = ""
    res_dict = asdict(ccno_des)
    res_dict["id"] = ccno_id_to_dict(ccno_des.id, trim)
    if trim:
        for key in detect_empty_dict_keys(res_dict):
            del res_dict[key]
    return res_dict
