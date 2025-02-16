from typing import Annotated, Any, final
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from saim.shared.parse.date import parse_rkms
from saim.shared.data_con.plugins.location import Location
from saim.shared.data_ops.clean import detect_empty_dict_keys
from saim.shared.parse.string import clean_text_rm_tags


def _fix_source(source: Any) -> str:
    if not isinstance(source, str):
        return ""
    clean = clean_text_rm_tags(source)
    if len(clean) > 1:
        return clean[0].upper() + clean[1:]
    return clean


@final
class Sample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    source: Annotated[str, AfterValidator(_fix_source), Field(min_length=1)] = ""
    location: Location = Field(default_factory=Location)
    date: Annotated[str, AfterValidator(parse_rkms)] = ""

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        loc = self.location.to_dict(trim)
        dict_res = self.model_dump(mode="python", exclude={"location"}, by_alias=True)
        dict_res["location"] = loc
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res
