from multiprocessing.context import SpawnContext
import time
from typing import Callable, Final, final
import warnings

from saim.shared.error.warnings import RequestWarn


_COOL_DOWN: Final[float] = 1.0
_T_RESET: Final[int] = 259200
_T_LIMIT: Final[int] = 3
_MAX_DELAY: Final[int] = 5


@final
class CoolDownDomain:
    __slots__: tuple[str, ...] = ("__domain", "__last_request", "__lock", "__timeout_cnt")

    def __init__(self, mpc: SpawnContext, domain: str, /) -> None:
        manager = mpc.Manager()
        self.__timeout_cnt = manager.Value("i", 0)
        self.__last_request = manager.Value("d", time.time() - _COOL_DOWN)
        self.__lock = manager.Lock()
        self.__domain = domain
        super().__init__()

    def call_after_cool_down(
        self, delay: float, callback: Callable[[float], tuple[float, bool]], /
    ) -> None:
        with self.__lock:
            last_req = self.__last_request.value
            cool_down_sec = delay if 0 < delay < _MAX_DELAY else _COOL_DOWN
            time_dif = time.time() - last_req
            time_out_cnt = self.__timeout_cnt.value
            if time_out_cnt >= _T_LIMIT and time_dif < _T_RESET:
                last_req = -1
            wait_time = cool_down_sec - time.time() + last_req
            new_req = last_req
            if wait_time > 0:
                new_req = last_req + wait_time
                self.__last_request.value = new_req
        if wait_time > 0:
            time.sleep(wait_time)
        if delay >= _MAX_DELAY:
            warnings.warn(
                f"[DELAY] High delay requirement detected - {self.__domain}",
                RequestWarn,
                stacklevel=2,
            )
        request_time, timeout = callback(last_req)
        with self.__lock:
            if self.__last_request.value == new_req:
                self.__last_request.value = request_time
            if timeout:
                cur_add = 0 if time_out_cnt >= _T_LIMIT else 1
                self.__timeout_cnt.value += cur_add
                info = "skipped" if last_req == -1 else "called"
                warnings.warn(
                    f"[TIMEOUT] {self.__domain} [{time_out_cnt} - {cur_add}] - {info}",
                    RequestWarn,
                    stacklevel=2,
                )
            else:
                if time_out_cnt > 0:
                    warnings.warn(
                        f"[TIMEOUT] {self.__domain} timeout reset",
                        RequestWarn,
                        stacklevel=2,
                    )
                self.__timeout_cnt.value = 0
