from typing import Annotated, final
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from saim.shared.data_ops.clean import detect_empty_dict_keys, filter_duplicates
from saim.shared.parse.geo import (
    check_country_code,
    check_lat,
    check_long,
    clean_place_name,
    clean_country,
    parse_lat_long,
)


@final
class Location(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    code: Annotated[str, AfterValidator(check_country_code)] = ""
    country: Annotated[
        str, AfterValidator(clean_place_name), AfterValidator(clean_country)
    ] = ""
    place: list[Annotated[str, AfterValidator(clean_place_name)]] = Field(
        default_factory=list
    )
    long: Annotated[str, AfterValidator(lambda val: parse_lat_long(val, check_long))] = (
        Field(default="", alias="longitude")
    )
    lat: Annotated[str, AfterValidator(lambda val: parse_lat_long(val, check_lat))] = (
        Field(default="", alias="latitude")
    )

    def to_dict(self, trim: bool = True, /) -> dict[str, list[str] | str]:
        dict_res: dict[str, list[str] | str] = self.model_dump(
            mode="python", exclude={"place"}, by_alias=True
        )
        dict_res["place"] = [
            cl_pla
            for pla_full in filter_duplicates(self.place)
            for pla in pla_full.split(",")
            if len(cl_pla := clean_place_name(pla)) >= 2
            and cl_pla.lower() != self.country.lower()
        ]
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res
