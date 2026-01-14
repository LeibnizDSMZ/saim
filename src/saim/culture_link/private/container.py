from dataclasses import dataclass, field
from typing import Iterator, final

from cafi.container.links import CatalogueLink
from pydantic import HttpUrl, ValidationError
from saim.culture_link.private.constants import (
    CAT_DET_EXP_DAYS,
    CAT_EXP_DAYS,
    HOME_EXP_DAYS,
    CacheNames,
    VerificationStatus,
)
from cafi.container.links import LinkLevel
from saim.shared.data_con.designation import CCNoDes


@final
@dataclass(frozen=True, slots=True)
class SearchTask:
    brc_id: int
    find_ccno: CCNoDes
    find_extra: list[str] = field(default_factory=list)

    @property
    def key(self) -> list[str]:
        return [
            self.find_ccno.acr.upper(),
            self.find_ccno.id.pre.upper(),
            self.find_ccno.id.core.upper(),
            self.find_ccno.id.suf.upper(),
            *map(lambda ext: ext.upper(), filter(lambda ext: ext != "", self.find_extra)),
        ]

    @property
    def ccno_key(self) -> str:
        key = ":".join(
            [
                self.find_ccno.acr.upper(),
                self.find_ccno.id.pre.upper(),
                self.find_ccno.id.core.upper(),
                self.find_ccno.id.suf.upper(),
            ]
        )
        return f"|{key}|"

    @property
    def extra_key(self) -> list[str]:
        return [f"|{extra.upper()}|" for extra in self.find_extra if extra != ""]


@final
@dataclass(frozen=True, slots=True)
class TaskPackage:
    task_id: int
    search_task: SearchTask
    template_links: CatalogueLink
    fallback_link: str = ""

    @property
    def urls(self) -> list[tuple[str, str, str, int]]:
        return [
            *[
                (
                    LinkLevel.cat.value,
                    *self._pack_catalogue(cat),
                )
                for cat in self.template_links.catalogue
            ],
            ("fallback", *self._pack_catalogue(self.fallback_link)),
            (
                LinkLevel.home.value,
                self.template_links.homepage,
                str(CacheNames.hom.value),
                HOME_EXP_DAYS,
            ),
        ]

    def _pack_catalogue(self, link: str, /) -> tuple[str, str, int]:
        if len(self.search_task.find_extra) == 0:
            return (link, str(CacheNames.cat.value), CAT_EXP_DAYS)
        return (link, str(CacheNames.cat_det.value), CAT_DET_EXP_DAYS)

    def __iter__(self) -> Iterator[tuple[str, str, str, int]]:
        return iter(task for task in self.urls)


@final
@dataclass(frozen=True, slots=True)
class LinkStatus:
    link: str
    link_type: str
    status: VerificationStatus

    def __post_init__(self) -> None:
        try:
            if self.link != "":
                object.__setattr__(self, "link", str(HttpUrl(self.link)))
        except ValidationError:
            object.__setattr__(self, "link", "")
        if self.link == "":
            object.__setattr__(self, "status", VerificationStatus.no_url)


@final
@dataclass(frozen=True, slots=True)
class LinkResult:
    link: str
    brc_id: int
    found_ccno: CCNoDes

    def __post_init__(self) -> None:
        try:
            if self.link != "":
                object.__setattr__(self, "link", str(HttpUrl(self.link)))
        except ValidationError:
            object.__setattr__(self, "link", "")


@final
@dataclass(frozen=True, slots=True)
class VerifiedURL:
    task_id: int
    result: LinkResult | None
    status: list[LinkStatus]


@final
@dataclass(frozen=True, slots=True)
class CachedPageResp:
    response: bytes = b""
    cached: bool = False
    status: int = 500
    timeout: bool = False
    prohibited: bool = False

    @staticmethod
    def change_to_cached_content(
        page: "CachedPageResp", new_content: bytes, /
    ) -> "CachedPageResp":
        return CachedPageResp(
            response=new_content,
            cached=True,
            status=page.status,
            timeout=page.timeout,
            prohibited=page.prohibited,
        )
