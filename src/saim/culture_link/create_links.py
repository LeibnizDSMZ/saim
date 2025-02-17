import atexit
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterable, Iterable, final

from cafi.constants.versions import CURRENT_VER
from cafi.library.catalogue import create_ccno_links
from cafi.container.links import CatalogueLink, LinkLevel
from saim.culture_link.private.container import SearchTask


from saim.culture_link.private.manager import (
    RequestManager,
    TaskPackage,
    VerifiedURL,
)
from saim.designation.manager import AcronymManager
from saim.shared.data_con.designation import CCNoDes
from saim.shared.cafi.adapter import get_domain_from_knacr, parse_ccno_to_cat_args


@final
@dataclass(frozen=True, slots=True)
class SearchRequest:
    find_ccno: str
    task_id: int
    find_extra: list[str] = field(default_factory=list)
    brc_id: int = -1
    fallback_link: str = ""
    exclude: tuple[LinkLevel, ...] = field(default_factory=tuple)


def _filter_domain_tasks(
    domain_tasks: dict[str, list[TaskPackage]],
    new_task: tuple[str, TaskPackage] | None = None,
    /,
) -> dict[str, list[TaskPackage]]:
    filtered = dict(filter(lambda item: len(item[1]) > 0, domain_tasks.items()))
    if new_task is not None:
        domain, task = new_task
        buf_list = filtered.get(domain, [])
        buf_list.append(task)
        filtered[domain] = buf_list
    return filtered


def create_ccno_brc_links(
    ccno: CCNoDes,
    acr_man: AcronymManager,
    bid: int,
    exclude: tuple[LinkLevel, ...] = (),
    /,
) -> list[tuple[int, CatalogueLink]]:
    if len(brc_ids := acr_man.identify_acr(ccno.acr)) > 0:
        return [
            (brc_id, create_ccno_links(acr_db, parse_ccno_to_cat_args(ccno), exclude))
            for brc_id in brc_ids
            if (bid < 1 or brc_id == bid)
            and (acr_db := acr_man.get_brc_by_id(brc_id)) is not None
        ]
    return []


@final
class CcnoLinkGenerator:
    __slots__: tuple[str, ...] = "__acr_man", "__manager", "__worker_cnt"

    def __init__(
        self,
        worker: int,
        work_dir: Path,
        db_size_gb: int = 100,
        acr_man: AcronymManager | None = None,
        /,
    ) -> None:
        acr = acr_man
        if acr is None:
            acr = AcronymManager(CURRENT_VER)
        self.__acr_man: AcronymManager = acr
        self.__manager = RequestManager(worker, work_dir, db_size_gb)
        self.__worker_cnt: int = worker
        atexit.register(lambda: self.__manager.close())
        super().__init__()

    @property
    def worker(self) -> int:
        return self.__worker_cnt

    def create_ccno_link_task(self, request: SearchRequest, /) -> TaskPackage | None:
        ccno_ided = self.__acr_man.identify_ccno(request.find_ccno)
        links = create_ccno_brc_links(
            ccno_ided, self.__acr_man, request.brc_id, request.exclude
        )
        if len(links) != 1:
            return None
        bid, link = links[0]
        if link.level == LinkLevel.emp and request.fallback_link == "":
            return None
        return TaskPackage(
            task_id=request.task_id,
            search_task=SearchTask(
                brc_id=bid,
                find_ccno=ccno_ided,
                find_extra=list(set(request.find_extra)),
            ),
            fallback_link=request.fallback_link,
            template_links=link,
        )

    def _create_domain_task(
        self, search_request: SearchRequest | None, /
    ) -> tuple[str, TaskPackage] | None:
        if search_request is None:
            return None
        task = self.create_ccno_link_task(search_request)
        if task is None:
            return None
        domain = get_domain_from_knacr(task.template_links, search_request.fallback_link)
        if domain == "":
            return None
        return (domain, task)

    def _create_work_package(
        self, domain_tasks: dict[str, list[TaskPackage]], /
    ) -> tuple[dict[str, list[TaskPackage]], list[TaskPackage]]:
        package: list[TaskPackage] = []
        while len(domain_tasks) > 0 and len(package) < self.__worker_cnt:
            cnt = len(package)
            package.extend(
                tasks.pop()
                for tasks in domain_tasks.values()
                if (cnt := cnt + 1) <= self.__worker_cnt
            )
            domain_tasks = _filter_domain_tasks(domain_tasks)
        return domain_tasks, package

    def create_work_packages(
        self, req_data: Iterable[SearchRequest], /
    ) -> Iterable[list[TaskPackage]]:
        req_iter = iter(req_data)
        domain_tasks: dict[str, list[TaskPackage]] = {}
        while (req := next(req_iter, None)) is not None or len(domain_tasks) > 0:
            domain_tasks = _filter_domain_tasks(
                domain_tasks, self._create_domain_task(req)
            )
            if len(domain_tasks) >= self.__worker_cnt or req is None:
                domain_tasks, package = self._create_work_package(domain_tasks)
                yield package

    async def verify_ccno_url(
        self, task_packages: Iterable[list[TaskPackage]], /
    ) -> AsyncIterable[VerifiedURL]:
        task_iter = iter(task_packages)
        tasks = next(task_iter, None)
        if tasks is not None:
            generator = self.__manager.verify_url(tasks)
            results = [anext(generator)]
            stack: list[TaskPackage] = []
            while len(results) > 0:
                try:
                    awaited = await results.pop()
                except StopAsyncIteration:
                    break
                yield awaited
                if len(stack) == 0 and (tasks := next(task_iter, None)) is not None:
                    stack.extend(tasks)
                try:
                    next_task = stack.pop() if len(stack) > 0 else None
                    result = generator.asend(next_task)
                    if result is not None:
                        results.append(result)
                except StopIteration:
                    pass

    async def simple_ccno_linking(
        self, ccnos: list[str], /
    ) -> AsyncIterable[VerifiedURL]:
        async for result in self.verify_ccno_url(
            self.create_work_packages(
                SearchRequest(find_ccno=ccno, task_id=tid)
                for tid, ccno in enumerate(ccnos)
            )
        ):
            yield result

    async def ccno_linking(
        self, requests: Iterable[SearchRequest], /
    ) -> AsyncIterable[VerifiedURL]:
        async for result in self.verify_ccno_url(self.create_work_packages(requests)):
            yield result
