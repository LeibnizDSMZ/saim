from typing import Annotated, Any, final
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from saim.shared.parse.date import ch_rkms
from saim.shared.data_con.plugins.location import Location
from saim.shared.data_ops.clean import detect_empty_dict_keys
from saim.shared.parse.source import fix_source
from saim.shared.parse.string import trim_edges


@final
class Sample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    source: Annotated[str | None, BeforeValidator(fix_source), Field(min_length=1)] = None
    location: Location = Field(default_factory=Location)
    date: Annotated[str | None, BeforeValidator(trim_edges), AfterValidator(ch_rkms)] = (
        None
    )

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        loc = self.location.to_dict(trim)
        dict_res = self.model_dump(mode="python", exclude={"location"}, by_alias=True)
        dict_res["location"] = loc
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res
