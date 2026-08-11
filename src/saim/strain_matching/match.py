from typing import Callable, Iterable, Sequence
from saim.designation.manager import AcronymManager
from saim.shared.data_con.designation import CCNoDesP
from saim.strain_matching.private.ccno_match import CCNoMatch
from saim.strain_matching.manager import MatchCache, UpdateResults
from saim.strain_matching.private.container import CulMatCon, CultureMatch, ErrCon
from saim.strain_matching.private.strain_match import StrainMatch


type MatchStrain = Callable[[Iterable[str]], set[int]]
type UpdateCache = Callable[[UpdateResults], None]


class _MatchWrapper[CT: CultureMatch]:
    __slots__ = ("__cache", "__ccno_match", "__strain_match", "__update")

    def __init__(
        self, acr_man: AcronymManager, cache: MatchCache, upd: bool, skip: bool, /
    ) -> None:
        super().__init__()
        self.__cache = cache
        self.__update = upd
        cache.check_consistency()
        self.__ccno_match: CCNoMatch[CT] = CCNoMatch(cache, acr_man)
        self.__strain_match: StrainMatch[CT] = StrainMatch(cache, acr_man, skip)

    def run_match(
        self,
        cul: CT,
        update: Callable[[CulMatCon[CT]], UpdateResults],
    ) -> ErrCon[CT] | None:
        mat_dep = self.__ccno_match.match(cul)
        if isinstance(mat_dep, ErrCon):
            return mat_dep
        mat_str = self.__strain_match.match(mat_dep)
        upd_res = update(mat_str)
        if self.__update:
            cul = mat_str.cul
            self.__cache.update_cache(upd_res)
        return None

    @property
    def cache_updater(self) -> UpdateCache:
        return self.__cache.update_cache

    @property
    def strain_matcher(self) -> MatchStrain:
        return self.__strain_match.match_strain


def _create_relation(
    rel_con: CultureMatch | list[str] | None, acr_manager: AcronymManager, /
) -> Sequence[CCNoDesP]:
    if rel_con is None:
        return []
    rel_con = rel_con if isinstance(rel_con, list) else rel_con.strain.relation
    return [
        ccno_des
        for rel in rel_con
        for ccno_des in acr_manager.identify_ccno_all_valid(rel)
        if ccno_des.acr != ""
    ]


def create_update_deposit[CT: CultureMatch](
    old_dep: CT | None,
    new_dep: CT | None,
    si_id: int,
    si_dp: int,
    acr_manager: AcronymManager,
    /,
) -> UpdateResults:
    if new_dep is None:
        return UpdateResults(si_id=si_id, si_dp=si_dp, used_in_update=False)
    return UpdateResults(
        si_id=si_id,
        si_dp=si_dp,
        used_in_update=True,
        cid=(new_dep.brc_id, new_dep.id.pre, new_dep.id.core, new_dep.id.suf),
        add_relations=_create_relation(new_dep, acr_manager),
        del_relations=_create_relation(old_dep, acr_manager),
    )


def create_update_relation(
    old_rel: list[str],
    new_rel: list[str],
    si_id: int,
    si_dp: int,
    acr_manager: AcronymManager,
    /,
) -> UpdateResults:
    to_add = _create_relation(new_rel, acr_manager)
    to_del = _create_relation(old_rel, acr_manager)
    if len(set(to_add) | set(to_del)) == 0:
        return UpdateResults(si_id=si_id, si_dp=si_dp, used_in_update=False)
    return UpdateResults(
        si_id=si_id,
        si_dp=si_dp,
        used_in_update=True,
        cid=None,
        add_relations=to_add,
        del_relations=to_del,
    )


type MatchF[CT] = Callable[
    [CT, Callable[[CulMatCon[CT]], UpdateResults]], ErrCon[CT] | None
]


def match_factory[CT: CultureMatch](
    con_type: type[CT], dry_run: bool = False, skip: bool = False, /
) -> Callable[[AcronymManager, MatchCache], tuple[MatchF[CT], MatchStrain, UpdateCache]]:
    print(f"creating matcher for type - {con_type!s}")
    to_update = not dry_run

    def wrap_init(
        acr_manager: AcronymManager, cache: MatchCache, /
    ) -> tuple[MatchF[CT], MatchStrain, UpdateCache]:
        matcher: _MatchWrapper[CT] = _MatchWrapper(acr_manager, cache, to_update, skip)
        return matcher.run_match, matcher.strain_matcher, matcher.cache_updater

    return wrap_init


def strain_match_factory(acr_manager: AcronymManager, cache: MatchCache) -> MatchStrain:
    cache.check_consistency()
    return StrainMatch(cache, acr_manager, True).match_strain
