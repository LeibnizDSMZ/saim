import asyncio
from datetime import timedelta
from io import BytesIO
import time
from typing import (
    Any,
    Awaitable,
    Callable,
    Concatenate,
    Mapping,
    ParamSpec,
    final,
    override,
)
import warnings
from requests import PreparedRequest, Timeout
from requests.structures import CaseInsensitiveDict
from requests.adapters import HTTPAdapter, BaseAdapter
from requests_cache import AnyResponse, BaseCache, CachedSession
from playwright.async_api import Response, async_playwright, Error, Browser, Playwright
from urllib3 import HTTPResponse
from requests.models import Response as RequestResponse
from requests.exceptions import RequestException
from saim.shared.misc.constants import ENCODING

from saim.culture_link.private.container import CachedPageResp
from saim.culture_link.private.cool_down import CoolDownDomain
from saim.culture_link.private.robots_txt import USER_AGENT, RobotsTxt
from saim.shared.error.exceptions import SessionCreationEx
from saim.shared.error.warnings import RequestWarn


async def _get_resp(
    call: Callable[[], Awaitable[Response | None]], err_str: str, /
) -> Response | None:
    resp: Response | None = None
    try:
        resp = await call()
    except Error as err:
        warnings.warn(f"{err!s} - {err_str}", RequestWarn, stacklevel=1)
        time.sleep(0.5)
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
    """Creates a cache key and is based on requests.adapters.HTTPAdapter

    LICENSE BSD 2-Clause "Simplified" License
    Copyright (c) 2019, Roman Haritonov
    Copyright (c) 2023, Jordan Cook
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


@final
class SimpleHTTPAdapter(HTTPAdapter):

    @override
    def close(self) -> None:
        pass

    def finish(self) -> None:
        print("CLOSING HTTP")
        super(HTTPAdapter, self).close()


@final
class BrowserPWAdapter(BaseAdapter):
    __slots__: tuple[str, ...] = ("__browser", "__pwc", "__retries", "__runner")

    def __init__(self, pwc: PWContext, max_retries: int = 0, /) -> None:
        self.__retries = max_retries
        self.__pwc: PWContext = pwc
        if not self.__pwc.is_test:
            ctx = self.__pwc.runner.run(self.__pwc.ctx)
            self.__browser: Browser | None = self.__pwc.runner.run(
                ctx.chromium.launch(
                    headless=True,
                    chromium_sandbox=True,
                    args=["--disable-gpu"],
                )
            )
        else:
            self.__browser = None
        super().__init__()

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
        page = await self.__browser.new_page(
            java_script_enabled=True, accept_downloads=False
        )
        page.on("console", lambda _: None)
        tout_msec = None
        await page.set_extra_http_headers({"User-Agent": USER_AGENT})
        if isinstance(timeout, (float, int)):
            tout_msec = timeout * 1000
            page.set_default_timeout(timeout=tout_msec)
            page.set_default_navigation_timeout(timeout=tout_msec)
        resp: Response | None = await _get_resp(
            lambda: page.goto(url, timeout=tout_msec, wait_until="load"), err_str
        )
        for _ in range(self.__retries):
            if resp is not None:
                break
            resp = await _get_resp(
                lambda: page.reload(timeout=tout_msec, wait_until="load"), err_str
            )
        start = time.time()
        wrapped: RequestResponse | None = None
        if resp is not None:
            await page.wait_for_load_state(state="domcontentloaded")
            if (tim_sl := 4 - (time.time() - start)) > 0:
                time.sleep(tim_sl)
            content = await page.content()
            wrapped = _create_response(request, resp, content)
        await page.close()
        return wrapped

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


def _mount_adapters(
    adapter_pw: BrowserPWAdapter | SimpleHTTPAdapter, session: CachedSession, /
) -> None:
    session.mount("http://", adapter_pw)
    session.mount("https://", adapter_pw)


P = ParamSpec("P")


def create_get_cache(
    adapter: BrowserPWAdapter | SimpleHTTPAdapter,
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
            allowable_codes=[200, 404, 403],
            allowable_methods=(
                "GET",
                "HEAD",
            ),
            key_fn=key_fn,
        )
        _mount_adapters(adapter, session)
    except Exception as cex:
        raise SessionCreationEx(f"{cex!s}") from cex
    return session


def run_request(browser: bool, session: CachedSession, /) -> Callable[..., AnyResponse]:
    if browser:
        return session.get
    return session.head


def _cr_request_params(browser: bool, /) -> dict[str, Any]:
    timeout_val = 100
    if browser:
        timeout_val *= 5
    return {
        "timeout": timeout_val,
        "allow_redirects": True,
        "headers": {"User-Agent": USER_AGENT},
    }


def _browser_fallback_wrap(
    browser: bool, pw_adapter: BrowserPWAdapter, session: CachedSession, url: str, /
) -> AnyResponse:
    params = _cr_request_params(browser)
    try:
        response = run_request(browser, session)(url, **params)
    except (Error, RequestException):
        if not browser:
            _mount_adapters(pw_adapter, session)
            response = session.get(url, **params)
        else:
            raise
    else:
        if not response.from_cache and response.status_code == 404 and not browser:
            response = session.get(url, **params)
    return response


def make_get_request(
    browser: bool,
    pw_adapter: BrowserPWAdapter,
    url: str,
    session: CachedSession,
    domain_info: tuple[CoolDownDomain, RobotsTxt],
    /,
) -> CachedPageResp:
    results = CachedPageResp(prohibited=True)
    cool_down, robots_txt = domain_info

    def _callback(last_request: float, /) -> tuple[float, bool]:
        if last_request < 0:
            return last_request, True
        nonlocal results
        request_time = time.time()
        try:
            response = _browser_fallback_wrap(browser, pw_adapter, session, url)
            if response.from_cache:
                request_time = last_request
        except (Error, RequestException):
            results = CachedPageResp(timeout=True)
            return request_time, True
        results = CachedPageResp(
            response=b"" if response.content is None else response.content,
            status=response.status_code,
            cached=response.from_cache,
        )
        return request_time, False

    if robots_txt.can_fetch(url):
        delay = robots_txt.get_delay()
        cool_down.call_after_cool_down(delay, _callback)
    return results
