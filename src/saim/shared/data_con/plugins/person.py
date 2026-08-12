from typing import Annotated, Any, Iterable, final
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from saim.shared.data_ops.clean import detect_empty_dict_keys
from saim.shared.parse.string import clean_text_rm_tags, trim_edges


@final
class PersonInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=False)

    name: Annotated[
        str | None, BeforeValidator(clean_text_rm_tags), Field(min_length=1)
    ] = None
    institute: Annotated[
        str | None, BeforeValidator(clean_text_rm_tags), Field(min_length=1)
    ] = None
    orcid: Annotated[str | None, BeforeValidator(trim_edges), Field(min_length=1)] = None
    ror: Annotated[str | None, BeforeValidator(trim_edges), Field(min_length=1)] = None

    def to_dict(self, trim: bool = True, /) -> dict[str, Any]:
        if trim and self.name is None and self.institute is None:
            return {}
        dict_res = self.model_dump(mode="python", by_alias=True)
        if trim:
            for key in detect_empty_dict_keys(dict_res):
                del dict_res[key]
        return dict_res

    @staticmethod
    def __rm_dup_per(people: list["PersonInfo"], /) -> Iterable["PersonInfo"]:
        buffer = set()
        for cop in people:
            pid = (cop.name, cop.institute, cop.orcid, cop.ror)
            if len(cop.to_dict(True)) > 0 and pid not in buffer:
                buffer.add(pid)
                yield cop

    @staticmethod
    def to_dict_people(
        people: list["PersonInfo"], trim: bool = True, /
    ) -> list[dict[str, Any]]:
        if trim and len(people) == 0:
            return []
        return [
            per_dict
            for per in PersonInfo.__rm_dup_per(people)
            if (per_dict := per.to_dict(trim)) or not trim
        ]
