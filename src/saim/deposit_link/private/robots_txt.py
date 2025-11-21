import math
from multiprocessing.context import SpawnContext
import time
from typing import Final, final
import requests
from requests import RequestException
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from saim.shared.misc.constants import ENCODING, VERSION

from saim.shared.error.exceptions import RequestURIEx


BOT_NAME: Final[str] = "saim"
USER_AGENT: Final[str] = f"{BOT_NAME}-bot/{VERSION}"
ROB_EXP_SEC: Final[int] = 86400


def get_user_agent(contact: str, /) -> str:
    if contact == "":
        return f"{USER_AGENT} (Python library)"
    return f"{USER_AGENT} (Python library; {contact})"


@final
class RobotsTxt:
    __slots__: tuple[str, ...] = (
        "__active",
        "__lock",
        "__modified",
        "__parser",
        "__robots_txt",
        "__url",
    )

    def __init__(self, url: str, mpc: SpawnContext, /) -> None:
        url_loc = urlparse(url)
        if (
            url_loc.hostname is None
            or url_loc.hostname == ""
            or url_loc.scheme not in ["http", "https"]
        ):
            raise RequestURIEx(f"Wrong URL format: {url} -  expected http(s)://route")
        self.__url = f"{url_loc.scheme}://{url_loc.netloc}/robots.txt"
        manager = mpc.Manager()
        self.__active = manager.Value("b", True)
        self.__modified = manager.Value("d", 0.0)
        self.__robots_txt = manager.Value("b", b"")
        self.__lock = manager.RLock()
        self.__update()
        super().__init__()

    def __fetch_robots_txt(self) -> None:
        with self.__lock:
            try:
                res = requests.get(self.__url, timeout=10)
                self.__active.value = res.status_code == 200
                if res.status_code == 200:
                    self.__robots_txt.value = res.text.encode(ENCODING)
            except RequestException:
                self.__active.value = False
            self.__modified.value = time.time()

    def __update(self) -> None:
        with self.__lock:
            update_dif = time.time() - self.__modified.value
            self.__parser = RobotFileParser()
            if self.__modified.value == 0 or update_dif > ROB_EXP_SEC:
                self.__fetch_robots_txt()
            self.__parser.parse(self.__robots_txt.value.decode(ENCODING).split("\n"))

    def can_fetch(self, url: str, /) -> bool:
        if not self.__active.value:
            return True
        self.__update()
        return self.__parser.can_fetch(BOT_NAME, url)

    def get_delay(self) -> int:
        if not self.__active.value:
            return 0
        self.__update()
        delay = self.__parser.crawl_delay(BOT_NAME)
        if (isinstance(delay, int) or (isinstance(delay, str) and delay.isdigit())) and (
            del_int := int(delay)
        ) > 0:
            return del_int
        request_rate = self.__parser.request_rate(BOT_NAME)
        if request_rate is not None:
            return math.ceil(request_rate.seconds / request_rate.requests)
        return 0
