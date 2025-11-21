from typing import Annotated, Any, Iterable, final
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from saim.shared.parse.string import trim_edges
from saim.shared.data_con.designation import CCNoIdP
from saim.shared.data_ops.clean import detect_empty_dict_keys
from typing import NamedTuple


class StrainCultureId(NamedTuple):
    s: int  # strain id
    c: int  # culture id


def _strip_designation(des: Any) -> Any:
    if isinstance(des, str) and len(des) > 61:
        return des[:61] + "..."
    return des


@final
class StrainCCNo(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_default=False)

    relation: list[
        Annotated[
            str,
            AfterValidator(trim_edges),
            AfterValidator(_strip_designation),
            Field(min_length=3),
        ]
    ] = Field(default_factory=list)
    strain_id: int | None = Field(default=None, alias="strainId")

    def __rm_dup_rel(self) -> Iterable[str]:
        buffer = set()
        for rel in self.relation:
            str_len = len(rel)
            if 2 < str_len <= 64 and rel not in buffer:
                buffer.add(rel)
                yield rel

    def patch_relation(self, main_acr: str, main_id: CCNoIdP, /) -> None:
        self.relation = list(
            rel
            for rel in self.__rm_dup_rel()
            if not (main_acr in rel and main_id.full in rel)
        )

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        rel = list(self.__rm_dup_rel())
        dict_res = self.model_dump(mode="python", exclude={"relation"}, by_alias=True)
        dict_res["relation"] = rel
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res


@final
class StrainFull(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid", validate_default=False)
    strain_id: int = Field(alias="strainId")
    main_id: int = Field(alias="mainId")
    type_strain: bool = Field(alias="typeStrain")
