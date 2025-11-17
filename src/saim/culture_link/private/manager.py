from collections.abc import Iterable
from multiprocessing import Queue
from multiprocessing.context import SpawnProcess
from pathlib import Path
from queue import Empty, Full
from typing import AsyncGenerator, Protocol, TypeAlias, final

from saim.culture_link.private.container import TaskPackage, VerifiedURL
from saim.culture_link.private.cool_down import CoolDownDomain
from saim.culture_link.private.robots_txt import RobotsTxt
from saim.culture_link.private.verify_ccno import VerifyCcNosProc
from saim.shared.misc.ctx import get_worker_ctx
from saim.shared.parse.http_url import get_domain

_ARGS_T: TypeAlias = tuple[TaskPackage, dict[str, tuple[CoolDownDomain, RobotsTxt]]]


class ValueP(Protocol):
    value: bool


@final
class RequestManager:
    __slots__: tuple[str, ...] = (
        "__contact",
        "__db_size_gb",
        "__domain_info",
        "__finish",
        "__mpc",
        "__queue_size",
        "__req",
        "__res",
        "__work_dir",
        "__worker",
    )

    def __init__(
        self, worker: int, work_dir: Path, db_size_gb: int, contact: str, /
    ) -> None:
        self.__work_dir: Path = work_dir
        self.__contact = contact
        self.__db_size_gb: int = db_size_gb
        if self.__db_size_gb < 1:
            self.__db_size_gb = 100
        self.__mpc = get_worker_ctx()
        worker_cnt = 1 if worker < 2 else worker
        self.__queue_size = worker_cnt * 4
        self.__domain_info: dict[str, tuple[CoolDownDomain, RobotsTxt]] = {}
        self.__req: Queue[_ARGS_T] = self.__mpc.Queue(maxsize=self.__queue_size)
        self.__res: Queue[VerifiedURL] = self.__mpc.Queue()
        self.__finish: ValueP = self.__mpc.Value("b", False)
        self.__worker = list(self.__create_workers(worker_cnt))
        for pro in self.__worker:
            pro.start()
        super().__init__()

    def __create_workers(self, worker: int, /) -> Iterable[SpawnProcess]:
        for _ in range(worker):
            yield self.__mpc.Process(
                target=VerifyCcNosProc(
                    self.__req,
                    self.__res,
                    self.__db_size_gb,
                    self.__work_dir,
                    self.__finish,
                    self.__contact,
                ).run
            )

    def __create_sub_domain(
        self, task: TaskPackage, /
    ) -> dict[str, tuple[CoolDownDomain, RobotsTxt]]:
        closed_domain = {}
        for _, url, *_ in task:
            if (domain := get_domain(url)) != "":
                if domain not in self.__domain_info:
                    self.__domain_info[domain] = (
                        CoolDownDomain(self.__mpc, domain),
                        RobotsTxt(url, self.__mpc),
                    )
                closed_domain[domain] = self.__domain_info[domain]
        return closed_domain

    async def __get_next_result(self) -> VerifiedURL | None:
        try:
            result = self.__res.get_nowait()
        except Empty:
            return None
        else:
            return result

    async def __put_next_request(self, request: _ARGS_T, /) -> bool:
        try:
            self.__req.put_nowait(request)
        except Full:
            return False
        else:
            return True

    async def verify_url(
        self, workload: list[TaskPackage], /
    ) -> AsyncGenerator[VerifiedURL, TaskPackage | None]:
        results_cnt: int = 0
        task_package_cnt = len(workload)
        tasks: list[TaskPackage] = [task for task in workload]
        while (task_cnt := len(tasks)) > 0 or task_package_cnt > results_cnt:
            buffered = 0
            while task_cnt > 0 and buffered < len(self.__worker):
                buffered += 1
                *_, task = tasks
                if not self.__req.full() and await self.__put_next_request(
                    (task, self.__create_sub_domain(task))
                ):
                    tasks.pop()
                    task_cnt -= 1
                else:
                    break

            if (result := await self.__get_next_result()) is not None:
                results_cnt += 1
                task_send = yield result
                if task_send is not None:
                    task_package_cnt += 1
                    tasks.append(task_send)

    def close(self) -> None:
        self.__finish.value = True
        for pro in self.__worker:
            pro.join()
            pro.close()
