from multiprocessing.context import SpawnContext
import time
from typing import Final, final
import warnings

from saim.shared.error.warnings import RequestWarn


_COOL_DOWN: Final[float] = 3.0
_T_RESET: Final[int] = 259200
_T_LIMIT: Final[float] = 3.0
_MAX_DELAY: Final[int] = 5


@final
class CoolDownDomain:
    __slots__: tuple[str, ...] = ("__domain", "__last_request", "__lock", "__timeout_cnt")

    def __init__(self, mpc: SpawnContext, domain: str, /) -> None:
        manager = mpc.Manager()
        self.__timeout_cnt = manager.Value("d", 0.0)
        last_req = time.time() - _COOL_DOWN
        if last_req < 0:
            last_req = time.time()
        self.__last_request = manager.Value("d", last_req)
        self.__lock = manager.Lock()
        self.__domain = domain
        super().__init__()

    def await_cool_down(self, delay: float, /) -> None:
        wait_time = 0.0
        cool_down_sec = delay if 0 < delay < _MAX_DELAY else _COOL_DOWN

        while True:
            with self.__lock:
                now = time.time()
                next_allowed = self.__last_request.value + cool_down_sec
                wait_time = max(0, next_allowed - now)

                if wait_time == 0:
                    self.__last_request.value = now
                    break
            time.sleep(wait_time + 0.01)

    def skip_request(self) -> bool:
        with self.__lock:
            last_req = self.__last_request.value
            timeout_cnt = self.__timeout_cnt.value
            if timeout_cnt < _T_LIMIT:
                return False
            if (time.time() - last_req) >= _T_RESET:
                self.__timeout_cnt.value = 0
                return False
        return True

    def finished_request(self, timeout: bool, tasks_cnt: int, /) -> None:
        with self.__lock:
            timeout_cnt = self.__timeout_cnt.value
            if not timeout and timeout_cnt > 0:
                self.__timeout_cnt.value = 0.0
            if timeout and timeout_cnt < _T_LIMIT:
                self.__timeout_cnt.value += 1.0 / tasks_cnt
                warnings.warn(
                    f"[TIMEOUT] {self.__domain} [{self.__timeout_cnt.value}]",
                    RequestWarn,
                    stacklevel=1,
                )
