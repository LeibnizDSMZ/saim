from typing import Annotated, Any, final

from pydantic import BaseModel, ConfigDict, Field

from saim.shared.data_con.plugins.location import Location
from saim.shared.data_con.plugins.person import Group
from saim.shared.data_ops.clean import detect_empty_dict_keys


@final
class Isolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    isolator: Group = Field(default_factory=Group)
    location: Location = Field(default_factory=Location)
    year: Annotated[int, Field(ge=1000)] | None = None

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        dict_res = self.model_dump(
            mode="python", exclude={"isolator", "location"}, by_alias=True
        )
        dict_res["isolator"] = self.isolator.to_dict(trim)
        dict_res["location"] = self.location.to_dict(trim)
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res


@final
class Deposition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    depositor: Group = Field(default_factory=Group)
    location: Location = Field(default_factory=Location)
    year: Annotated[int, Field(ge=1000)] | None = None

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        dict_res = self.model_dump(
            mode="python", exclude={"depositor", "location"}, by_alias=True
        )
        dict_res["depositor"] = self.depositor.to_dict(trim)
        dict_res["location"] = self.location.to_dict(trim)
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res
