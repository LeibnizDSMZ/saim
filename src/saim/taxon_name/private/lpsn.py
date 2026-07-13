import atexit
from pathlib import Path
import time
from typing import Any, Callable, Final, final
from requests.exceptions import RequestException
from requests_cache import CachedSession
from urllib import parse

from saim.shared.cache.request import (
    create_simple_get_cache,
    create_sqlite_backend,
)
from saim.shared.data_con.taxon import (
    DomainE,
    GBIFRanksE,
    is_domain,
    is_rank,
    parse_domain,
    parse_rank,
)
from saim.shared.jwt.key_cloak import JWTCred
from saim.taxon_name.private.container import LPSNId, LPSNName, LpsnOrgC

LPSN_API: Final[str] = "https://api.lpsn.dsmz.de/"
LPSN_ADV: Final[str] = f"{LPSN_API}advanced_search?"
LPSN_ORG: Final[str] = f"{LPSN_API}fetch/"


def _create_header(lpsn_cred: JWTCred, /) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {lpsn_cred.token.access}",
    }


def _request_next(
    req_next: str | None,
    lpsn_cred: JWTCred,
    session: CachedSession,
    last_req: Callable[[float], float],
    cnt: int = 1,
    /,
) -> dict[str, Any] | None:
    if req_next is None or req_next == "" or cnt > 3:
        return None
    err_401 = False
    headers = _create_header(lpsn_cred)
    time.sleep(last_req(time.time()))
    try:
        res = session.get(req_next, headers=headers, timeout=60)
        if res.status_code == 200 and isinstance((resd := res.json()), dict):
            if res.from_cache:
                last_req(0.0)
            return resd
        elif res.status_code == 401:
            err_401 = True
    except RequestException as exc:
        if exc.response is not None and exc.response.status_code == 401:
            err_401 = True
    if err_401:
        lpsn_cred.refresh()
        return _request_next(req_next, lpsn_cred, session, last_req, cnt + 1)
    return None


def _request_lpsn_ad(
    name: str,
    session: CachedSession,
    lpsn_cred: JWTCred,
    last_req: Callable[[float], float],
    /,
) -> list[tuple[str, int]]:
    if name == "":
        return []
    req_url = f"{LPSN_ADV}taxon-name={parse.quote(name)}&match_mode=exact"
    res_con = LPSNName(next=req_url, results=[])
    lids: list[tuple[str, int]] = []
    while (
        res_buf := _request_next(res_con.next, lpsn_cred, session, last_req)
    ) is not None:
        res_con = LPSNName(**res_buf)
        lids.extend((name, lid) for lid in res_con.results if lid > 0)
    return lids


def _request_lpsn_org(
    lpsn_id: int,
    session: CachedSession,
    lpsn_cred: JWTCred,
    last_req: Callable[[float], float],
    /,
) -> list[LpsnOrgC]:
    if lpsn_id < 1:
        return []
    req_url = f"{LPSN_ORG}{lpsn_id}"
    res_con = LPSNId(next=req_url, results=[])
    while (
        res_buf := _request_next(res_con.next, lpsn_cred, session, last_req)
    ) is not None:
        res_con = LPSNId(**res_buf)
        return res_con.results
    return []


def _get_lpsn_correct_name(
    con: LpsnOrgC,
    session: CachedSession,
    lpsn_cred: JWTCred,
    last_req: Callable[[float], float],
    /,
) -> list[tuple[str, int]]:
    if (
        con.lpsn_correct_name_id is None
        or con.lpsn_correct_name_id < 1
        or con.id == con.lpsn_correct_name_id
    ):
        return [(con.full_name, con.id)]
    return [
        (con.full_name, con.id)
        for con in _request_lpsn_org(
            con.lpsn_correct_name_id, session, lpsn_cred, last_req
        )
        if con.id > 0
    ]


@final
class LpsnTaxReq:
    __slots__ = (
        "__correct_name_cache",
        "__exp_days",
        "__kcl",
        "__last_req",
        "__name_cache",
        "__org_cache",
        "__session",
        "__work_dir",
    )

    def __init__(
        self, work_dir: Path, exp_days: int, user: str, upw: str, kurl: str, /
    ) -> None:
        self.__exp_days = exp_days
        self.__last_req: float = 0.0
        self.__work_dir = work_dir
        # TODO list in cache only occur because of fetch and possible next, even if it
        # never happens, should be replaced in linkatlas or here at a later time
        self.__org_cache: dict[int, list[LpsnOrgC]] = {}
        self.__name_cache: dict[str, list[tuple[str, int]]] = {}
        self.__correct_name_cache: dict[int, list[tuple[str, int]]] = {}
        # ---
        self.__session, self.__kcl = self.__create_session(user, upw, kurl)
        super().__init__()
        atexit.register(lambda: self.__session.close())  # type: ignore

    def __create_session(
        self, user: str, upw: str, url: str, /
    ) -> tuple[CachedSession, JWTCred]:
        backend = create_sqlite_backend("taxon_name_lpsn", self.__work_dir)(
            10, self.__exp_days
        )
        kcl = JWTCred(user, upw, "api.lpsn.public", url)
        return create_simple_get_cache(self.__exp_days, backend), kcl

    def __cwt(self, time: float, /) -> float:
        wait_time = 1 - (time - self.__last_req)
        self.__last_req = time
        if wait_time < 0:
            return 0
        if wait_time > 1:
            return 1
        return wait_time

    def __get_org_cache(self, lpsn_id: int, /) -> list[LpsnOrgC]:
        if lpsn_id < 1:
            return []
        if lpsn_id in self.__org_cache:
            return self.__org_cache[lpsn_id]

        org_data = _request_lpsn_org(
            lpsn_id, self.__session, self.__kcl, lambda call: self.__cwt(call)
        )
        self.__org_cache[lpsn_id] = org_data
        return org_data

    def __get_name_cache(self, name: str, /) -> list[tuple[str, int]]:
        if name == "":
            return []
        if name in self.__name_cache:
            return self.__name_cache[name]

        name_id = _request_lpsn_ad(
            name, self.__session, self.__kcl, lambda call: self.__cwt(call)
        )
        result = []
        if len(name_id) > 0:
            result = [
                (name, lid)
                for name, lid in name_id
                if lid > 0
                for res in self.__get_org_cache(lid)
                if res.full_name == name
            ]
            self.__name_cache[name] = result
        return result

    def __get_correct_name_cache(self, lpsn_id: int, /) -> list[tuple[str, int]]:
        if lpsn_id < 1:
            return []
        if lpsn_id in self.__correct_name_cache:
            return self.__correct_name_cache[lpsn_id]
        result = [
            name_id_c
            for res in self.__get_org_cache(lpsn_id)
            for name_id_c in _get_lpsn_correct_name(
                res, self.__session, self.__kcl, lambda call: self.__cwt(call)
            )
            if name_id_c[1] > 0
        ]
        self.__correct_name_cache[lpsn_id] = result
        return result

    def get_name(self, names: list[str], /) -> list[tuple[str, int]]:
        for name in names:
            res = self.__get_name_cache(name)
            if len(res) > 0:
                return res
        return []

    def __get_rank_name(self, lpsn_id: int, rank: GBIFRanksE, /) -> str:
        if lpsn_id < 1:
            return ""

        current_rank = self.get_rank(lpsn_id)
        if current_rank == rank:
            org_data = self.__get_org_cache(lpsn_id)
            if len(org_data) > 0:
                return org_data[0].full_name.upper()

        org_data = self.__get_org_cache(lpsn_id)
        for res in org_data:
            if res.lpsn_parent_id is not None:
                parent_name = self.__get_rank_name(res.lpsn_parent_id, rank)
                if parent_name != "":
                    return parent_name
        return ""

    def get_genus(self, lpsn_id: int, /) -> str:
        return self.__get_rank_name(lpsn_id, GBIFRanksE.gen)

    def get_species(self, lpsn_id: int, /) -> str:
        return self.__get_rank_name(lpsn_id, GBIFRanksE.spe)

    def get_domain(self, lpsn_id: int, /) -> DomainE:
        domain_name = self.__get_rank_name(lpsn_id, GBIFRanksE.dom)
        if not is_domain(domain_name):
            return DomainE.ukn
        return parse_domain(domain_name)

    def get_correct_name(self, name: str, lpsn_id: int = -1, /) -> list[tuple[str, int]]:
        if lpsn_id > 0:
            name_id = [("", lpsn_id)]
        else:
            name_id = self.get_name([name])
        if len(name_id) == 0:
            return []
        return [
            name_id_c
            for _, lid in name_id
            if lid > 0
            for name_id_c in self.__get_correct_name_cache(lid)
        ]

    def get_rank(self, lpsn_id: int, /) -> GBIFRanksE:
        org_data = self.__get_org_cache(lpsn_id)
        for res in org_data:
            rank = res.category.upper()
            if is_rank(rank):
                return parse_rank(rank)
        return GBIFRanksE.oth

    def get_correct_id(self, lpsn_id: int | None, /) -> int | None:
        if lpsn_id is None:
            return None
        org_data = self.__get_org_cache(lpsn_id)
        for res in org_data:
            cid = res.lpsn_correct_name_id
            if cid is not None and cid > 0:
                return cid
        return None

    def get_type_strain(self, lpsn_id: int, /) -> set[str]:
        typ_str: set[str] = set()
        org_data = self.__get_org_cache(lpsn_id)
        for res in org_data:
            typ_str.update(res.type_strain_names)
        return typ_str
