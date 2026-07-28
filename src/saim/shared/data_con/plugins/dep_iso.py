from typing import Annotated, Any, final

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from saim.shared.data_con.plugins.location import Location
from saim.shared.data_con.plugins.person import PersonInfo
from saim.shared.data_ops.clean import detect_empty_dict_keys


@final
class Isolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    isolator: list[PersonInfo] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    year: Annotated[int, Field(ge=1000)] | None = None

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        dict_res = self.model_dump(
            mode="python", exclude={"isolator", "location"}, by_alias=True
        )
        dict_res["isolator"] = PersonInfo.to_dict_people(self.isolator, trim)
        dict_res["location"] = self.location.to_dict(trim)
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res


@final
class Deposition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    depositor: list[PersonInfo] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    year: Annotated[int, Field(ge=1000)] | None = None

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        dict_res = self.model_dump(
            mode="python", exclude={"depositor", "location"}, by_alias=True
        )
        dict_res["depositor"] = PersonInfo.to_dict_people(self.depositor, trim)
        dict_res["location"] = self.location.to_dict(trim)
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res


def _validate_person_info(per: PersonInfo) -> PersonInfo:
    if not per.orcid or not per.name:
        raise ValueError("ORCID and Name must be provided!")
    return per


@final
class Registration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    submitter: Annotated[PersonInfo, AfterValidator(_validate_person_info)] = Field(
        default_factory=PersonInfo
    )
    supervisor: Annotated[PersonInfo, AfterValidator(_validate_person_info)] = Field(
        default_factory=PersonInfo
    )

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        dict_res = self.model_dump(
            mode="python", exclude={"submitter", "supervisor"}, by_alias=True
        )
        dict_res["submitter"] = self.submitter.to_dict(trim)
        dict_res["supervisor"] = self.supervisor.to_dict(trim)
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res
