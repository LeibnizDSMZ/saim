from typing import Annotated, Any, final

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from saim.shared.data_con.plugins.location import Location
from saim.shared.data_con.plugins.person import PersonInfo
from saim.shared.data_ops.clean import detect_empty_dict_keys
from saim.shared.parse.general import pa_int
from saim.shared.parse.person import ch_person_info


@final
class Isolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    isolator: Annotated[list[PersonInfo], Field(min_length=1)] = Field(
        default_factory=list
    )
    location: Location = Field(default_factory=Location)
    year: Annotated[int | None, BeforeValidator(pa_int), Field(ge=1000)] = None

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

    depositor: Annotated[list[PersonInfo], Field(min_length=1)] = Field(
        default_factory=list
    )
    location: Location = Field(default_factory=Location)
    year: Annotated[int | None, BeforeValidator(pa_int), Field(ge=1000)] = None

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


@final
class Registration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    submitter: Annotated[PersonInfo, AfterValidator(ch_person_info)] = Field(
        default_factory=PersonInfo
    )
    supervisor: Annotated[PersonInfo, AfterValidator(ch_person_info)] = Field(
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
