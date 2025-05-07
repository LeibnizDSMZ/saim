import atexit
from pathlib import Path
import time
from typing import Callable, Final, final
from urllib import parse
import requests
from saim.shared.cache.request import create_simple_get_cache, create_sqlite_backend
from saim.shared.data_con.taxon import GBIFRanksE, GBIFTypeE
from requests_cache import CachedSession
from saim.shared.parse.string import clean_text_rm_enclosing
from saim.taxon_name.private.container import GBIF, GBIFName

_GBIF_API: Final[str] = "https://api.gbif.org/v1/parser/name"


def _select_genus(genus: str, name: str, typ: GBIFTypeE, /) -> bool:
    if genus == "":
        return False
    return typ == GBIFTypeE.inf and name[-1] == "."


def _get_name_gbif(gbif: GBIFName, /) -> GBIF:
    if gbif.type == GBIFTypeE.vir or gbif.canon_mark == "":
        return GBIF(
            name=clean_text_rm_enclosing(gbif.sci_name).replace("'", "").replace('"', ""),
            rank_marker=gbif.rank,
        )
    if _select_genus(gbif.genus, gbif.canon_mark, gbif.type):
        return GBIF(name=gbif.genus, rank_marker=GBIFRanksE.unr)
    return GBIF(name=gbif.canon_mark, rank_marker=gbif.rank)


def _analyse_gbif_response(ori: str, res: requests.Response, /) -> GBIF:
    res_con = res.json()
    if not isinstance(res_con, list):
        return GBIF(name=ori)
    for org in res_con:
        gbif_api = GBIFName(**org)
        if gbif_api.sci_name != "":
            return _get_name_gbif(gbif_api)
    return GBIF(name=ori)


def _request_gbif(
    name: str, session: CachedSession, last_req: Callable[[float], float], /
) -> GBIF:
    if name == "":
        return GBIF()
    req = f"{_GBIF_API}?name={parse.quote(name)}"
    if (res := session.get(req, timeout=60)).status_code == 200:
        if not res.from_cache:
            time.sleep(last_req(time.time()))
        return _analyse_gbif_response(name, res)
    return GBIF(name=name)


@final
class GbifTaxReq:
    __slots__ = ("__exp_days", "__last_req", "__session", "__work_dir")

    def __init__(self, work_dir: Path, exp_days: int, /) -> None:
        self.__exp_days = exp_days
        self.__last_req: float = 0.0
        self.__work_dir = work_dir
        self.__session: CachedSession = self.__create_session()
        super().__init__()
        atexit.register(lambda: self.__session.close())  # type: ignore

    def __create_session(self) -> CachedSession:
        backend = create_sqlite_backend("taxon_name_gbif", self.__work_dir)(
            10, self.__exp_days
        )
        return create_simple_get_cache(self.__exp_days, backend)

    def __cwt(self, time: float, /) -> float:
        wait_time = 1 - (time - self.__last_req)
        self.__last_req = time
        if wait_time < 0:
            return 0
        if wait_time > 1:
            return 1
        return wait_time

    def get_rank(self, tax_nam: str, /) -> GBIFRanksE:
        if tax_nam == "":
            return GBIFRanksE.oth
        return _request_gbif(
            tax_nam, self.__session, lambda call: self.__cwt(call)
        ).rank_marker

    def get_name(self, tax_nam: str, /) -> str:
        if tax_nam == "":
            return tax_nam
        return _request_gbif(tax_nam, self.__session, lambda call: self.__cwt(call)).name
