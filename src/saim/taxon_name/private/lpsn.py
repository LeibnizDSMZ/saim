import atexit
from pathlib import Path
import time
from typing import Callable, Final, final
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


def _request_next[RT: (LPSNName, LPSNId)](
    req_res: RT,
    lpsn_cred: JWTCred,
    session: CachedSession,
    cont: type[RT],
    cnt: int = 1,
    /,
) -> tuple[RT, bool] | None:
    if req_res.next is None or req_res.next == "" or cnt > 3:
        return None
    err_401 = False
    headers = _create_header(lpsn_cred)
    try:
        res = session.get(req_res.next, headers=headers, timeout=60)
        if res.status_code == 200:
            return cont(**res.json()), res.from_cache
        elif res.status_code == 401:
            err_401 = True
    except RequestException as exc:
        if exc.response is not None and exc.response.status_code == 401:
            err_401 = True
    if err_401:
        time.sleep(1)
        lpsn_cred.refresh()
        return _request_next(req_res, lpsn_cred, session, cont, cnt + 1)
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
    req_url = f"{LPSN_ADV}taxon-name={parse.quote(name)}"
    res_con = LPSNName(next=req_url, results=[])
    lids: list[tuple[str, int]] = []
    while (new_res := _request_next(res_con, lpsn_cred, session, LPSNName)) is not None:
        res_con, from_cache = new_res
        lids.extend((name, lid) for lid in res_con.results if lid > 0)
        if not from_cache:
            time.sleep(last_req(time.time()))
    return lids


def _request_lpsn_org_pure(
    lpsn_id: int,
    session: CachedSession,
    lpsn_cred: JWTCred,
    last_req: Callable[[float], float],
    /,
) -> list[LpsnOrgC]:
    req_url = f"{LPSN_ORG}{lpsn_id}"
    res_con = LPSNId(next=req_url, results=[])
    nam: list[LpsnOrgC] = []
    while (new_res := _request_next(res_con, lpsn_cred, session, LPSNId)) is not None:
        res_con, from_cache = new_res
        nam.extend(con for con in res_con.results)
        if not from_cache:
            time.sleep(last_req(time.time()))
        return nam
    return []


def _request_lpsn_org(
    lpsn_id: int,
    session: CachedSession,
    lpsn_cred: JWTCred,
    last_req: Callable[[float], float],
    /,
) -> list[LpsnOrgC]:
    if lpsn_id < 1:
        return []
    return _request_lpsn_org_pure(lpsn_id, session, lpsn_cred, last_req)


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
    __slots__ = ("__exp_days", "__kcl", "__last_req", "__session", "__work_dir")

    def __init__(
        self, work_dir: Path, exp_days: int, user: str, upw: str, kurl: str, /
    ) -> None:
        self.__exp_days = exp_days
        self.__last_req: float = 0.0
        self.__work_dir = work_dir
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

    def get_name(self, names: list[str], /) -> list[tuple[str, int]]:
        for name in names:
            name_id = _request_lpsn_ad(
                name, self.__session, self.__kcl, lambda call: self.__cwt(call)
            )
            if len(name_id) > 0:
                return [
                    (name, lid)
                    for name, lid in name_id
                    if lid > 0
                    for res in _request_lpsn_org(
                        lid,
                        self.__session,
                        self.__kcl,
                        lambda call: self.__cwt(call),
                    )
                    if res.full_name == name
                ]
        return []

    def __get_rank_name(self, lpsn_id: int, rank: GBIFRanksE, /) -> str:
        for res in _request_lpsn_org_pure(
            lpsn_id,
            self.__session,
            self.__kcl,
            lambda call: self.__cwt(call),
        ):
            if self.get_rank(lpsn_id) == rank and lpsn_id > 0:
                return res.full_name.upper()
            if res.lpsn_parent_id is not None:
                res_name = self.__get_rank_name(res.lpsn_parent_id, rank)
                if res_name != "":
                    return res_name
        return ""

    def get_genus(self, lpsn_id: int, /) -> str:
        if lpsn_id < 1:
            return ""
        return self.__get_rank_name(lpsn_id, GBIFRanksE.gen)

    def get_species(self, lpsn_id: int, /) -> str:
        if lpsn_id < 1:
            return ""
        return self.__get_rank_name(lpsn_id, GBIFRanksE.spe)

    def get_domain(self, lpsn_id: int, /) -> DomainE:
        if lpsn_id < 1:
            return DomainE.ukn
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
            for res in _request_lpsn_org(
                lid, self.__session, self.__kcl, lambda call: self.__cwt(call)
            )
            for name_id_c in _get_lpsn_correct_name(
                res, self.__session, self.__kcl, lambda call: self.__cwt(call)
            )
            if name_id_c[1] > 0
        ]

    def get_rank(self, lpsn_id: int, /) -> GBIFRanksE:
        if lpsn_id < 1:
            return GBIFRanksE.oth
        for res in _request_lpsn_org(
            lpsn_id, self.__session, self.__kcl, lambda call: self.__cwt(call)
        ):
            rank = res.category.upper()
            if is_rank(rank):
                return parse_rank(rank)
        return GBIFRanksE.oth

    def get_correct_id(self, lpsn_id: int | None, /) -> int | None:
        if lpsn_id is None or lpsn_id < 1:
            return None
        for res in _request_lpsn_org(
            lpsn_id, self.__session, self.__kcl, lambda call: self.__cwt(call)
        ):
            cid = res.lpsn_correct_name_id
            if cid is not None and cid > 0:
                return cid
        return None

    def get_type_strain(self, lpsn_id: int, /) -> set[str]:
        typ_str: set[str] = set()
        if lpsn_id < 1:
            return typ_str
        for res in _request_lpsn_org(
            lpsn_id,
            self.__session,
            self.__kcl,
            lambda call: self.__cwt(call),
        ):
            typ_str.update(res.type_strain_names)
        return typ_str
