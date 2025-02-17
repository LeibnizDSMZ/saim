import asyncio
import atexit
from pathlib import Path
import tempfile
from cafi.library.loader import load_catalogue_db, load_regex_db
from cafi.container.acr_db import AcrDbEntry
from cafi.container.links import LinkLevel
from cafi.container.fun.format import url_to_str
from saim.culture_link.create_links import CcnoLinkGenerator, SearchRequest
from saim.designation.manager import AcronymManager


def _create_search_request_homepage(
    cc_db: dict[int, AcrDbEntry], reg_db: dict[int, list[str]], /
) -> list[SearchRequest]:
    return [
        SearchRequest(
            find_ccno=reg_db.get(acr_id, [""])[0],
            task_id=task_id,
            brc_id=acr_id,
            exclude=(LinkLevel.cat,),
        )
        for task_id, (acr_id, acr_entry) in enumerate(cc_db.items())
        if url_to_str(acr_entry.homepage) != ""
    ]


def _create_search_request_catalogue(
    cat_db: dict[int, list[str]], /
) -> list[SearchRequest]:
    tasks = []
    task_id = 0
    for acr_id, cat_ex in cat_db.items():
        for ccno in cat_ex:
            tasks.append(
                SearchRequest(
                    find_ccno=ccno,
                    task_id=task_id,
                    brc_id=acr_id,
                    exclude=(LinkLevel.home,),
                )
            )
            task_id += 1
    return tasks


async def _verify_links(
    linker: CcnoLinkGenerator, link_requests: list[SearchRequest], /
) -> None:
    verified_task_ids = set()
    results = {}
    async for link in linker.ccno_linking(link_requests):
        print(f"TASK ID - {link.task_id} - [done]")
        results[link.task_id] = link
        if link.result is not None and link.result.link != "":
            print(f"\\-> BRC ID - {link.result.brc_id} - [verified]")
            verified_task_ids.add(link.task_id)
    print("VERIFICATION FINISHED! printing results --->")
    for link_req in link_requests:
        task_id = link_req.task_id
        if task_id not in verified_task_ids:
            print(f"ERROR: {link_req.brc_id} - {results.get(task_id, link_req)!s}")
    print("<---")


def validate_knacr(version: str, worker: int, db_size: int, output: str, /) -> None:
    if output == "" or not (work_dir := Path(output)).is_dir():
        tmp = tempfile.TemporaryDirectory()
        atexit.register(lambda: tmp.cleanup())
        work_dir = Path(tmp.name)
    acr_man = AcronymManager(version)
    cat_db = load_catalogue_db(acr_man.brc_container.cc_db, version)
    reg_db = load_regex_db(acr_man.brc_container.cc_db, version)
    linker = CcnoLinkGenerator(
        worker,
        work_dir,
        db_size,
    )
    print("VERIFY HOMEPAGES")
    asyncio.run(
        _verify_links(
            linker, _create_search_request_homepage(acr_man.brc_container.cc_db, reg_db)
        )
    )
    print("VERIFY CATALOGUES")
    asyncio.run(_verify_links(linker, _create_search_request_catalogue(cat_db)))
    print("--- DONE ---")
