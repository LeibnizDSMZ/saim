from typing import Annotated, final
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from saim.shared.data_ops.clean import detect_empty_dict_keys, filter_duplicates
from saim.shared.parse.geo import (
    ch_country_code,
    ch_lat,
    ch_long,
    clean_place_name,
    clean_country,
    pa_lat_long,
)
from saim.shared.parse.string import trim_edges


@final
class Location(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    code: Annotated[
        str | None,
        BeforeValidator(trim_edges),
        Field(min_length=2, max_length=2),
        AfterValidator(ch_country_code),
    ] = None
    country: Annotated[
        str | None,
        BeforeValidator(clean_place_name),
        BeforeValidator(clean_country),
        Field(min_length=1),
    ] = None
    place: list[Annotated[str, AfterValidator(clean_place_name)]] = Field(
        default_factory=list
    )
    long: Annotated[str | None, AfterValidator(lambda val: pa_lat_long(val, ch_long))] = (
        Field(default=None, alias="longitude")
    )
    lat: Annotated[str | None, AfterValidator(lambda val: pa_lat_long(val, ch_lat))] = (
        Field(default=None, alias="latitude")
    )

    def to_dict(self, trim: bool = True, /) -> dict[str, list[str] | str]:
        dict_res: dict[str, list[str] | str] = self.model_dump(
            mode="python", exclude={"place"}, by_alias=True
        )
        dict_res["place"] = [
            cl_pla
            for pla in filter_duplicates(
                ele for con in self.place for ele in con.split(",")
            )
            if len(cl_pla := clean_place_name(pla)) >= 2
            and (self.country is None or cl_pla.lower() != self.country.lower())
        ]
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res
