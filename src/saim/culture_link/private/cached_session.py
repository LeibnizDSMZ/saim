import asyncio
from datetime import timedelta
from io import BytesIO
import random
import tempfile
import time
from typing import (
    Awaitable,
    Callable,
    Concatenate,
    Final,
    Mapping,
    ParamSpec,
    final,
)
import warnings
from requests import PreparedRequest, Timeout
from requests.structures import CaseInsensitiveDict
from requests.adapters import BaseAdapter
from requests_cache import BaseCache, CachedSession
from playwright.async_api import (Response, async_playwright, Error,
                                  BrowserContext, Playwright, Page)
from urllib3 import HTTPResponse
from requests.models import Response as RequestResponse
from requests.exceptions import RequestException
from saim.shared.misc.constants import ENCODING

from saim.culture_link.private.container import CachedPageResp
from saim.culture_link.private.cool_down import CoolDownDomain
from saim.culture_link.private.robots_txt import RobotsTxt, get_user_agent
from saim.shared.error.exceptions import SessionCreationEx
from saim.shared.error.warnings import RequestWarn


async def _get_resp(
    call: Callable[[], Awaitable[Response | None]], err_str: str, retry: int, /
) -> Response | None:
    resp: Response | None = None
    try:
        resp = await call()
    except Error as err:
        warnings.warn(
            f"{retry!s} - {err!s} - {resp!s} - {err_str}",
            RequestWarn,
            stacklevel=0
        )
    return resp


def _wrap_playwright_response(
    req: PreparedRequest, resp: Response, body: str, /
) -> HTTPResponse:
    response = HTTPResponse(
        body=BytesIO(body.encode(ENCODING)),
        headers=resp.headers,
        status=resp.status,
        reason=resp.status_text,
        preload_content=True,
        decode_content=False,
        request_method=req.method,
        request_url=req.url,
        auto_close=False,
    )
    response.close()
    return response


def _create_response(
    req: PreparedRequest, resp: Response, content: str, /
) -> RequestResponse:
    """Creates a cache key and is based on requests.adapters.HTTPAdapter.

    License:
        BSD 2-Clause "Simplified" License

    Copyright:
        (c) 2019, Roman Haritonov
        (c) 2023, Jordan Cook
    """
    # based on requests.adapters.HTTPAdapter
    response = RequestResponse()
    response.status_code = resp.status
    response.headers = CaseInsensitiveDict(resp.headers)
    response.encoding = ENCODING
    response.raw = _wrap_playwright_response(req, resp, content)
    response._content = content.encode(ENCODING)
    response.reason = resp.status_text
    response.url = req.url if req.url is not None else ""
    response.request = req
    return response


@final
class PWContext:
    __slots__: tuple[str, ...] = ("__cnt", "__runner", "__spw", "__test")

    def __init__(self, cnt: int, test: bool = False) -> None:
        self.__cnt: int = cnt
        self.__spw: Playwright | None = None
        self.__test = test
        self.__runner: asyncio.Runner | None = asyncio.Runner()
        if not self.__test:
            self.runner.run(self.ctx)
        super().__init__()

    @property
    def runner(self) -> asyncio.Runner:
        if self.__runner is None:
            self.__runner = asyncio.Runner()
        return self.__runner

    @property
    def is_test(self) -> bool:
        return self.__test

    @property
    async def ctx(self) -> Playwright:
        if self.__test:
            raise SessionCreationEx("ctx should not be called in tests")
        if self.__spw is None:
            ctx = await async_playwright().start()
            self.__spw = ctx
        return self.__spw

    def close(self, last: bool) -> None:
        self.__cnt -= 0 if last else 1
        if not last and self.__cnt > 0:
            return None
        if self.__spw is not None:
            self.runner.run(self.__spw.stop())
            self.__spw = None
        runner = self.__runner
        if runner is not None:
            self.__runner = None
            runner.close()


BLOCK_TYPES: Final[list[str]] = [
    "image",
    "media",
    "font",
    "ping",
    "manifest",
    "prefetch",
]


@final
class BrowserPWAdapter(BaseAdapter):
    __slots__: tuple[str, ...] = (
        "__browser",
        "__contact",
        "__cool_down",
        "__delay",
        "__pwc",
        "__retries",
        "__runner",
        "__tmp"
    )

    def __init__(
        self,
        pwc: PWContext,
        contact: str = "",
        max_attempts: int = 1,
        /
    ) -> None:
        self.__pwc: PWContext = pwc
        self.__contact = contact
        self.__tmp = tempfile.TemporaryDirectory()
        self.__cool_down : CoolDownDomain | None = None
        self.__delay = 1.0
        self.__retries = max_attempts if max_attempts > 1 else 1
        if not self.__pwc.is_test:
            ctx = self.__pwc.runner.run(self.__pwc.ctx)
            self.__browser: BrowserContext | None = self.__pwc.runner.run(
                ctx.chromium.launch_persistent_context(
                    user_data_dir=self.__tmp.name,
                    headless=True,
                    chromium_sandbox=True,
                    java_script_enabled=True,
                    accept_downloads=False,
                    args=["--disable-gpu"],
                )
            )
        else:
            self.__browser = None
        super().__init__()

    def set_cool_down(self, cool_down: CoolDownDomain, delay: float, /) -> None:
        self.__cool_down = cool_down
        self.__delay = delay

    async def __await_cool_down(self) -> None:
        if self.__cool_down is None:
            await asyncio.sleep(1.0)
        else:
            self.__cool_down.await_cool_down(self.__delay)

    async def __send(
        self,
        url: str,
        request: PreparedRequest,
        timeout: float | tuple[float, float] | tuple[float, None] | None = None,
        err_str: str = "",
        /,
    ) -> RequestResponse | None:
        if self.__browser is None:
            raise SessionCreationEx("browser not started")
        tout_msec = 30_000.0
        if isinstance(timeout, (float, int)):
            tout_msec = timeout * 1000.0
        for attempt in range(self.__retries):
            page = await self.__browser.new_page()
            await page.route(
                "**/*",
                lambda route, req: (
                    route.abort()
                    if req.resource_type in BLOCK_TYPES else route.continue_()
                ),
            )
            page.on("console", lambda _: None)
            await page.set_extra_http_headers(
                {"User-Agent": get_user_agent(self.__contact)}
            )
            att_time = tout_msec * (0.5 if attempt > 0 else 1.0)
            async def go_to_page(p: Page = page, t: float = att_time) -> Response | None:
                return await p.goto(url, timeout=t, wait_until="load")
            await self.__await_cool_down()
            resp: Response | None = await _get_resp(go_to_page, err_str, attempt +1)
            if resp is not None:
                start_time = time.time()
                try:
                    await page.wait_for_load_state("networkidle", timeout=60_000.0)
                except Error:
                    pass
                else:
                    elapsed = time.time() - start_time
                    remaining = max(0, 6 - elapsed)
                    if remaining > 0:
                        await asyncio.sleep(remaining)
                content = await page.content()
                await page.close()
                return _create_response(request, resp, content)
            await page.close()
            if attempt + 1 < self.__retries:
                await asyncio.sleep(1.0 + (random.random() - 0.5)) # noqa: S311
        return None

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: None | bytes | str | tuple[bytes | str, bytes | str] = None,
        proxies: Mapping[str, str] | None = None,
    ) -> RequestResponse:
        err_str = f"{request.url!s}, {stream!s}, {timeout!s}, {verify!s}, {cert!s},"
        err_str += f" {proxies!s}"
        response = None
        url = request.url
        if url is not None and url != "":
            response = self.__pwc.runner.run(self.__send(url, request, timeout, err_str))
        if response is not None:
            return response
        raise Timeout(request, None)

    def close(self) -> None:
        pass

    def finish(self) -> None:
        print("CLOSING PW")
        if self.__browser is not None:
            self.__pwc.runner.run(self.__browser.close())
        self.__pwc.close(False)
        self.__tmp.cleanup()


P = ParamSpec("P")


def _create_get_cache(
    adapter: BrowserPWAdapter,
    exp_days: int,
    backend: BaseCache,
    key_fn: Callable[Concatenate[PreparedRequest, P], str],
    /,
) -> CachedSession:
    try:
        session = CachedSession(
            backend=backend,
            expire_after=timedelta(days=exp_days),
            cache_control=False,
            stale_if_error=False,
            always_revalidate=False,
            allowable_codes=[*range(200, 400), 404, 403],
            allowable_methods=(
                "GET",
            ),
            key_fn=key_fn,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    except Error as cex:
        raise SessionCreationEx(f"{cex!s}") from cex
    return session


def make_get_request(
    url: str,
    session: tuple[
        BrowserPWAdapter,
        int,
        BaseCache,
        Callable[Concatenate[PreparedRequest, P], str],
    ],
    info: tuple[CoolDownDomain, RobotsTxt, str],
    tasks_cnt: int,
    /,
) -> CachedPageResp:
    results = CachedPageResp(prohibited=True)
    cool_down, robots_txt, contact = info
    pw_adapter, exp, cache, call  = session

    pw_adapter.set_cool_down(cool_down, robots_txt.get_delay())
    cached_session = _create_get_cache(pw_adapter, exp, cache, call, )

    if robots_txt.can_fetch(url):
        if cool_down.skip_request():
            return results
        try:
            response = cached_session.get(url, **{
                "timeout": 180,
                "allow_redirects": True,
                "headers": {"User-Agent": get_user_agent(contact)},
            })
        except (Error, RequestException):
            cool_down.finished_request(True, tasks_cnt)
            return CachedPageResp(timeout=True)
        results = CachedPageResp(
            response=b"" if response.content is None else response.content,
            status=response.status_code,
            cached=response.from_cache,
        )
    cool_down.finished_request(results.timeout, tasks_cnt)
    return results
