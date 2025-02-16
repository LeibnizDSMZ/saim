from typing import Annotated, Any, Iterable, final
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from saim.shared.data_ops.clean import detect_empty_dict_keys
from saim.shared.parse.string import clean_text_rm_tags, trim_edges


@final
class PersonInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    name: Annotated[str, AfterValidator(clean_text_rm_tags), Field(min_length=1)] = ""
    institute: Annotated[str, AfterValidator(clean_text_rm_tags), Field(min_length=1)] = (
        ""
    )
    orcid: Annotated[str, AfterValidator(trim_edges), Field(min_length=1)] = ""
    ror: Annotated[str, AfterValidator(trim_edges), Field(min_length=1)] = ""

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        if trim and self.name == "" and self.institute == "":
            return {}
        dict_res = self.model_dump(mode="python", by_alias=True)
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res


@final
class Group(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    main: PersonInfo = Field(default_factory=PersonInfo)
    coop: list[PersonInfo] = Field(default_factory=list)

    def __rm_dup_coop(self) -> Iterable[PersonInfo]:
        buffer = set()
        for cop in self.coop:
            pid = (cop.name, cop.institute, cop.orcid, cop.ror)
            if len(cop.to_dict(True)) > 0 and pid not in buffer:
                buffer.add(pid)
                yield cop

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        main = self.main.to_dict(trim)
        if trim and len(main) == 0:
            return {}
        dict_res = {
            "main": main,
            "coop": [cop.to_dict(trim) for cop in self.__rm_dup_coop()],
        }
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res
