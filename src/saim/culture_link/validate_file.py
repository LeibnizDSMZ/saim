import asyncio
import atexit
import csv
import json
from pathlib import Path
import tempfile
import time

from saim.culture_link.create_links import CcnoLinkGenerator, SearchRequest
from saim.designation.manager import AcronymManager


def read_tasks(task_file: Path, /) -> list[SearchRequest]:
    tasks = []
    with task_file.open() as tfh:
        for line in csv.reader(tfh, delimiter=",", quotechar='"'):
            tasks.append(
                SearchRequest(
                    find_ccno=line[2],
                    task_id=int(line[0]),
                    find_extra=[
                        extra_cl
                        for extra in line[3].split(",")
                        if (extra_cl := extra.strip()) != ""
                    ],
                    brc_id=int(line[1]) if line[1].isdigit() else -1,
                    fallback_link=line[4],
                )
            )
    return tasks


def _gen_out_path(output: str, in_file: Path, /) -> tuple[Path, Path]:
    if output == "" or not (out_path := Path(output)).is_dir():
        suc = f"{in_file.absolute()!s}.res.json"
        fail = f"{in_file.absolute()!s}.fail.json"
        return Path(suc), Path(fail)
    suc = f"{in_file.name!s}.res.json"
    fail = f"{in_file.name!s}.fail.json"
    return out_path.joinpath(suc), out_path.joinpath(fail)


async def _verify_links(
    linker: CcnoLinkGenerator,
    link_requests: list[SearchRequest],
    output: str,
    in_file: Path,
    /,
) -> None:
    failed, success, start = {}, {}, time.time()
    task_num = 0
    async for link in linker.ccno_linking(link_requests):
        task_num += 1
        calc_time = int((time.time() - start) / 36) / 100
        print(f"TASK ID - {link.task_id} - [done] - [{task_num}/{len(link_requests)}]")
        prog = int(task_num / len(link_requests) * 100)
        print(f"\\-> Time - {calc_time}h - progress - {prog}%")
        if link.result is not None and link.result.link != "":
            print(f"\\-> BRC ID - {link.result.brc_id} - [verified]")
            success[link.task_id] = {
                "brc_id": link.result.brc_id,
                "link": link.result.link,
                "link_type": list(
                    filter(
                        lambda status: link.result is not None
                        and status.link == link.result.link,
                        link.status,
                    )
                )
                .pop()
                .link_type,
                "status": [
                    {"link": status.link, "reason": str(status.status.value)}
                    for status in link.status
                ],
            }
        else:
            failed[link.task_id] = {
                "result": link.result,
                "status": [
                    {
                        "link": status.link,
                        "type": status.link_type,
                        "reason": str(status.status.value),
                    }
                    for status in link.status
                ],
            }
    print("<---")
    s_out, f_out = _gen_out_path(output, in_file)
    with s_out.open("w") as sfh:
        json.dump(success, sfh)
    with f_out.open("w") as ffh:
        json.dump(failed, ffh)


def validate_file(
    version: str, worker: int, db_size: int, output: str, in_file: Path, /
) -> None:
    if output == "" or not (work_dir := Path(output)).is_dir():
        tmp = tempfile.TemporaryDirectory()
        atexit.register(lambda: tmp.cleanup())
        work_dir = Path(tmp.name)
    linker = CcnoLinkGenerator(worker, work_dir, db_size, AcronymManager(version))
    print("VERIFY FILE")
    asyncio.run(_verify_links(linker, read_tasks(in_file), output, in_file))
    print("--- DONE ---")
