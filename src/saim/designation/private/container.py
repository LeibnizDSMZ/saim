from typing import Annotated, final

from pydantic import BaseModel, ConfigDict, Field


@final
class _AltCodes(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    description: str = ""


@final
class _GColCon(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", validate_default=False)

    name: Annotated[str, Field(min_length=1)]
    active: bool
    per_col: bool = Field(alias="personalCollection")
    con_types: list[str] = Field(alias="contentTypes", default_factory=list)
    alt_codes: list[_AltCodes] = Field(alias="alternativeCodes")
    code: Annotated[str, Field(min_length=1)] = ""
    homepage: Annotated[str, Field(min_length=1)] = ""
    inst_name: Annotated[str, Field(min_length=1)] = Field(
        default="", alias="institutionName"
    )
    inst_code: Annotated[str, Field(min_length=1)] = Field(
        default="", alias="institutionCode"
    )


@final
class _GInsCon(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", validate_default=False)

    name: Annotated[str, Field(min_length=1)]
    active: bool
    add_names: list[Annotated[str, Field(min_length=1)]] = Field(alias="additionalNames")
    alt_codes: list[_AltCodes] = Field(alias="alternativeCodes")
    type: str = ""
    code: Annotated[str, Field(min_length=1)] = ""
    homepage: Annotated[str, Field(min_length=1)] = ""
    cat_url: Annotated[str, Field(min_length=1)] = Field(default="", alias="catalogUrl")


@final
class GbifColRes(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int
    limit: int
    end_of_rec: bool = Field(alias="endOfRecords")
    count: int
    results: list[_GColCon] = Field(default_factory=list)


@final
class GbifInsRes(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int
    limit: int
    end_of_rec: bool = Field(alias="endOfRecords")
    count: int
    results: list[_GInsCon] = Field(default_factory=list)


@final
class NcbiIC(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    inst_code: Annotated[str, Field(min_length=1)]
    synonyms: set[Annotated[str, Field(min_length=1)]]
    inst_name: Annotated[str, Field(min_length=1)]


@final
class NcbiCC(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    coll_code: Annotated[str, Field(min_length=1)]
    coll_name: Annotated[str, Field(min_length=1)]
    collection_type: str
