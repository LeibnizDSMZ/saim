import atexit
import copy
from dataclasses import dataclass
from hashlib import sha256
from multiprocessing.queues import Queue
from pathlib import Path
from queue import Empty
from re import Pattern
import re
from typing import Any, Final, Protocol, TypeAlias, final
import warnings
from requests import Response
from requests_cache import (
    PreparedRequest,
    SerializerPipeline,
    Stage,
    create_key,
    yaml_serializer,
)
from saim.culture_link.private.cached_session import (
    BrowserPWAdapter,
    PWContext,
    make_get_request,
)
from saim.culture_link.private.constants import CacheNames, VerificationStatus
from saim.culture_link.private.container import (
    CachedPageResp,
    LinkResult,
    LinkStatus,
    SearchTask,
    TaskPackage,
    VerifiedURL,
)
from saim.culture_link.private.cool_down import CoolDownDomain
from saim.culture_link.private.robots_txt import RobotsTxt
from saim.designation.extract_ccno import DEF_SUF_RM
from saim.shared.cache.request import create_sqlite_backend
from saim.shared.misc.constants import ENCODING
from saim.shared.data_con.designation import CCNoDes
from saim.shared.error.exceptions import KnownException
from saim.shared.parse.http_url import get_domain
from saim.shared.error.warnings import ClosureWarn, ValidationWarn


def _wrap_status(
    status_code: int, timeout: bool, prohibited: bool, missing: bool, /
) -> VerificationStatus:
    if prohibited:
        return VerificationStatus.prohibited
    if timeout:
        return VerificationStatus.timeout
    match status_code:
        case code if 200 <= code < 400:
            if missing:
                return VerificationStatus.mis_ele
            return VerificationStatus.ok
        case 404:
            return VerificationStatus.fail_404
        case 403:
            return VerificationStatus.fail_403
        case _:
            return VerificationStatus.fail_status


_REQ: TypeAlias = dict[str, tuple[CoolDownDomain, RobotsTxt]]
_ARGS_T: TypeAlias = tuple[TaskPackage, _REQ]
_ARGS_ST: TypeAlias = tuple[TaskPackage, _REQ, int, Path, BrowserPWAdapter | None, str]
_WSP: Final[Pattern[str]] = re.compile(r"\s+")


@final
@dataclass(frozen=True, slots=True)
class SessionSettings:
    pw_adapter: BrowserPWAdapter
    url: str
    name: str
    exp_days: int
    db_size_gb: int
    work_dir: Path
    contact: str


def _is_string_in_text(text: str, to_find: list[str], /) -> bool:
    for task in to_find:
        for word in task.split(" "):
            if (
                word.strip() != ""
                and re.compile(re.escape(_WSP.sub(" ", word).upper())).search(text)
                is None
            ):
                return False
    return True


def _is_ccno_in_text(text: str, to_find: CCNoDes, /) -> bool:
    return (
        re.compile(
            r"(?:\W+|$)?".join(
                [
                    r"(?:" + re.escape(to_find.acr.upper()) + r")?",
                    re.escape(to_find.id.pre.upper()),
                    r"0*" + re.escape(to_find.id.core.upper()),
                    r"["
                    + "".join(re.escape(suf) for suf in to_find.id.suf.upper())
                    + "".join(
                        set(
                            re.escape(suf.upper())
                            for suf_con in DEF_SUF_RM
                            for suf in suf_con
                        )
                    )
                    + r"]{"
                    + f"{len(to_find.id.suf)}"
                    + r",}",
                ]
            )
            + r"(?:\W|$)"
        ).search(text)
        is not None
    )


def _find_elements_in_content(content: bytes, sea_task: SearchTask, /) -> bool:
    upper_text = content.decode(encoding=ENCODING).upper()
    if not _is_ccno_in_text(upper_text, sea_task.find_ccno):
        return False
    if not _is_string_in_text(upper_text, sea_task.find_extra):
        return False
    return True


def _serialize_results(
    resp: Response, sea_task: SearchTask, skip_search: bool, /
) -> Response:
    c_resp: Response = copy.copy(resp)
    if 200 <= c_resp.status_code < 400 and skip_search:
        c_resp._content = "ONLY PINGED".encode(ENCODING)
        return c_resp
    if 200 <= c_resp.status_code < 400 and _find_elements_in_content(
        c_resp.content, sea_task
    ):
        extra = " - ".join(sea_task.extra_key)
        sea_res = f"{sea_task.ccno_key} - {extra}"
        c_resp._content = sea_res.encode(ENCODING)
        return c_resp
    c_resp._content = b""
    return c_resp


def _prepare_result_cached(
    link: str, resp: CachedPageResp, sea_task: SearchTask, skip_search: bool, /
) -> LinkResult | None:
    if resp.status < 200 or resp.status >= 400:
        return None
    if not skip_search:
        content = resp.response.decode(ENCODING)
        if sea_task.ccno_key not in content:
            return None
        for sea_ext in sea_task.extra_key:
            if sea_ext not in content:
                return None
    return LinkResult(link=link, brc_id=sea_task.brc_id, found_ccno=sea_task.find_ccno)


def _prepare_result_raw(
    link: str, resp: CachedPageResp, sea_task: SearchTask, skip_search: bool, /
) -> LinkResult | None:
    if resp.status < 200 or resp.status >= 400:
        return None
    warnings.warn(
        f"[SERIALIZATION] {link} - was parsed without removing its content!",
        ClosureWarn,
        stacklevel=2,
    )
    if skip_search or _find_elements_in_content(resp.response, sea_task):
        return LinkResult(
            link=link, brc_id=sea_task.brc_id, found_ccno=sea_task.find_ccno
        )
    return None


def _create_custom_key(
    sea_task: SearchTask, request: PreparedRequest, **kwargs: Any
) -> str:
    base_key = create_key(request, **kwargs)
    key = sha256()
    key.update(base_key.encode("utf-8"))
    for sea_key in sea_task.key:
        key.update(sea_key.encode("utf-8"))
    return key.hexdigest()


def _get_result(
    settings: SessionSettings,
    domain: tuple[CoolDownDomain, RobotsTxt],
    sea_task: SearchTask,
    tasks_cnt: int,
    /,
) -> tuple[CachedPageResp, LinkResult | None]:
    skip_search = settings.name == str(CacheNames.hom.value)
    buffered: bytes = b""
    closure: bool = False

    def wrap_ser_f(response: Response) -> Response:
        nonlocal buffered
        nonlocal closure
        serialized = _serialize_results(response, sea_task, skip_search)
        if isinstance(serialized.content, bytes):
            buffered = serialized.content
            closure = True
        return serialized

    def wrap_key_f(request: PreparedRequest, **kwargs: Any) -> str:
        if skip_search:
            return create_key(request, **kwargs)
        return _create_custom_key(sea_task, request, **kwargs)

    custom_ser_p = SerializerPipeline(
        [
            Stage(dumps=wrap_ser_f, loads=lambda resp: resp),
            *yaml_serializer.stages,
        ],
        name="yaml_slim",
        is_binary=False,
    )
    backend = create_sqlite_backend(
        f"verify_ccno_{settings.name}", settings.work_dir, custom_ser_p
    )(settings.db_size_gb, settings.exp_days)
    resp = make_get_request(
        settings.url,
        (settings.pw_adapter, settings.exp_days, backend, wrap_key_f),
        (*domain, settings.contact),
        tasks_cnt,
    )
    if not resp.cached and closure:
        resp = CachedPageResp.change_to_cached_content(resp, buffered)
    if resp.cached:
        return resp, _prepare_result_cached(settings.url, resp, sea_task, skip_search)
    return resp, _prepare_result_raw(settings.url, resp, sea_task, skip_search)


def _create_pw_adapter(
    adapter: BrowserPWAdapter | None, contact: str, /
) -> BrowserPWAdapter:
    if adapter is not None:
        return adapter
    return BrowserPWAdapter(PWContext(2), contact, 3)


def verify_ccno_in_url(args: _ARGS_ST, /) -> VerifiedURL:
    task, cool_down, size, folder, pwa, contact = args
    status = []
    try:
        for url_typ, url, name, exp in task:
            domain = cool_down.get(get_domain(url), None)
            if url == "" or domain is None:
                continue
            resp, ana_result = _get_result(
                SessionSettings(
                    _create_pw_adapter(pwa, contact),
                    url,
                    name,
                    exp,
                    size,
                    folder,
                    contact,
                ),
                domain,
                task.search_task,
                len(task.urls),
            )
            status.append(
                LinkStatus(
                    link=url,
                    link_type=url_typ,
                    status=_wrap_status(
                        resp.status, resp.timeout, resp.prohibited, ana_result is None
                    ),
                )
            )
            if ana_result is not None:
                return VerifiedURL(task_id=task.task_id, result=ana_result, status=status)
    except KnownException as kex:
        warnings.warn(kex.message, ValidationWarn, stacklevel=2)
        return VerifiedURL(
            task_id=task.task_id,
            result=None,
            status=[LinkStatus(link="", link_type="", status=VerificationStatus.err)],
        )

    if len(status) == 0:
        status.append(LinkStatus(link="", link_type="", status=VerificationStatus.no_url))
    return VerifiedURL(task_id=task.task_id, result=None, status=status)


class ValueP(Protocol):
    @property
    def value(self) -> bool: ...


@final
class VerifyCcNosProc:
    __slots__: tuple[str, ...] = (
        "__contact",
        "__finish",
        "__folder",
        "__pw_adapter",
        "__read",
        "__size",
        "__write",
    )

    def __init__(
        self,
        read: Queue[_ARGS_T],
        write: Queue[VerifiedURL],
        size: int,
        folder: Path,
        finish: ValueP,
        contact: str,
        /,
    ) -> None:
        self.__read: Queue[_ARGS_T] = read
        self.__write: Queue[VerifiedURL] = write
        self.__size = size
        self.__folder = folder
        self.__finish: ValueP = finish
        self.__contact = contact
        self.__pw_adapter: BrowserPWAdapter | None = None
        atexit.register(lambda: self.close())
        super().__init__()

    @property
    def _pw_adapter(self) -> BrowserPWAdapter:
        self.__pw_adapter = _create_pw_adapter(self.__pw_adapter, self.__contact)
        return self.__pw_adapter

    def __verify_ccno_in_url(self, args: _ARGS_T, /) -> VerifiedURL:
        task, req = args
        return verify_ccno_in_url(
            (
                task,
                req,
                self.__size,
                self.__folder,
                self._pw_adapter,
                self.__contact,
            )
        )

    def run(self) -> None:
        print("[LINKER] STARTED")
        while not self.__finish.value:
            try:
                request = self.__read.get(timeout=0.5)
            except (TimeoutError, Empty):
                pass
            else:
                result = self.__verify_ccno_in_url(request)
                self.__write.put(result)

    def close(self) -> None:
        if self.__pw_adapter is not None:
            self.__pw_adapter.finish()
            self.__pw_adapter = None
