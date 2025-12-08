from collections.abc import Sequence
from datetime import datetime, timedelta
import itertools
from pathlib import Path
from re import Pattern
import re
from typing import Callable, Concatenate, Final, Iterable, Protocol, Self, final
import warnings

from pydantic import ValidationError

from saim.shared.data_con.taxon import (
    DomainE,
    GBIFRanksE,
    has_virus_in_name,
    is_informative_rank,
)
from saim.shared.error.exceptions import GlobalManagerEx, RequestURIEx, ValidationEx
from saim.shared.error.warnings import ManagerWarn
from saim.shared.parse.general import pa_int
from saim.shared.search.radix_tree import RadixTree, radix_add
from saim.taxon_name.extract_taxa import extract_taxa_from_text
from saim.taxon_name.private.container import (
    CorTaxonNameId,
    DomainId,
    GenusId,
    LPSNConf,
    RankId,
    SpeciesId,
    TaxonName,
    TaxonOV,
)

from saim.shared.parse.string import clean_text_rm_tags
from saim.taxon_name.private.gbif import GbifTaxReq
from saim.taxon_name.private.lpsn import LpsnTaxReq
from saim.taxon_name.private.ncbi import (
    NcbiTaxReq,
)


def _verify_date[**P, T](
    func: Callable[Concatenate["TaxonManager", P], T],
) -> Callable[Concatenate["TaxonManager", P], T]:
    def wrap(self: "TaxonManager", *args: P.args, **kwargs: P.kwargs) -> T:
        if datetime.now() - timedelta(days=self._exp_days) > self._start:
            self._ncbi = NcbiTaxReq(self.working_directory, self._exp_days, True)
            self._nid_sg = None
            self._radix_sg = None
        return func(self, *args, **kwargs)

    return wrap


def _fill_con[K, T, V](
    container: dict[K, T],
    results: list[tuple[K, V]],
    fill: Callable[[T, V], None],
    create: Callable[[K], T],
    /,
) -> None:
    for key, nid in results:
        if key not in container:
            container[key] = create(key)
        fill(container[key], nid)


_FIRST_WORD: Final[Pattern[str]] = re.compile(r"^([A-Z][a-z]+).*$")


def _create_extra_names_domain(name: str, /) -> list[str]:
    names = [name]
    if has_virus_in_name(name):
        names.append(DomainE.vir.value[0] + DomainE.vir.value[1:].lower())
    elif (f_word := _FIRST_WORD.match(name)) is not None and (
        core := f_word.group(1)
    ) is not None:
        names.append(core)
    return names


class _IdP(Protocol):
    @property
    def ncbi(self) -> set[int]: ...
    @property
    def lpsn(self) -> set[int]: ...


def _keep_ids(ncbi: int, lpsn: int, id_con: _IdP, /) -> bool:
    if lpsn > 0 and lpsn in id_con.lpsn:
        return True
    if ncbi > 0 and ncbi in id_con.ncbi:
        return True
    return lpsn <= 0 and ncbi <= 0


_NAME_CLEAN = (
    re.compile(r"\s+spp?\.$"),
    re.compile(r"\s+cv\.$"),
)


@final
class TaxonManager:

    __slots__ = (
        "__gbif",
        "__jump",
        "__lpsn",
        "__wir",
        "_exp_days",
        "_ncbi",
        "_nid_sg",
        "_radix_sg",
        "_start",
    )
    __instance: Self | None = None

    def __init__(self, work_dir: Path, lpsn_conf: LPSNConf, /) -> None:
        self.__wir = work_dir
        self._exp_days = 14
        self._start = datetime.now()
        self.__gbif, self._ncbi, self.__lpsn = self.__create_session(lpsn_conf)
        self._radix_sg: None | RadixTree[int] = None
        self._nid_sg: None | dict[int, str] = None
        self.__jump = 0
        super().__init__()

    def __new__(cls, *_args: Path | str) -> Self:
        if cls.__instance is not None:
            return cls.__instance
        cls.__instance = super().__new__(cls)
        return cls.__instance

    def __create_session(
        self, cnf: LPSNConf, /
    ) -> tuple[GbifTaxReq, NcbiTaxReq, LpsnTaxReq]:

        try:
            return (
                GbifTaxReq(self.__wir, self._exp_days),
                NcbiTaxReq(self.__wir, self._exp_days),
                LpsnTaxReq(self.__wir, self._exp_days, cnf.user, cnf.pw, cnf.url),
            )
        except (RequestURIEx, ValidationEx, ValidationError) as exc:
            warnings.warn(
                f"Taxon manager could not be started {exc!s}",
                ManagerWarn,
                stacklevel=2,
            )
        raise GlobalManagerEx("Could not initialize taxon cache")

    @property
    def working_directory(self) -> Path:
        return self.__wir

    def __prep_name(self, name: str, /) -> tuple[str, str]:
        cleaned = clean_text_rm_tags(name)
        if len(cleaned) > 1:
            cleaned = cleaned[0].upper() + cleaned[1:]
        for cleaner in _NAME_CLEAN:
            cleaned = cleaner.sub("", cleaned)
        return (
            cleaned,
            self.__gbif.get_name(cleaned),
        )

    @_verify_date
    def get_patched_name(self, name: str, /) -> str:
        cl_name, tax_name = self.__prep_name(name)
        names_id = self.__lpsn.get_name([tax_name, cl_name])
        if len(names_id) > 0:
            return names_id[0][0]
        names_id = self._ncbi.get_name([tax_name, cl_name])
        if len(names_id) > 0:
            return names_id[0][0]
        if len(cl_name) >= 3:
            return cl_name
        return ""

    @_verify_date
    def get_correct_name(
        self, name: str, ncbi_id: int = -1, lpsn_id: int = -1, /
    ) -> list[CorTaxonNameId]:
        cor_names: dict[str, CorTaxonNameId] = {}
        cl_name, _ = self.__prep_name(name)

        def fun(nam: str) -> CorTaxonNameId:
            return CorTaxonNameId(name=nam)

        ncbi = self._ncbi.get_correct_name(cl_name, ncbi_id)
        lpsn = self.__lpsn.get_correct_name(cl_name, lpsn_id)
        _fill_con(cor_names, ncbi, lambda con, nid: con.ncbi.add(nid), fun)
        _fill_con(cor_names, lpsn, lambda con, lid: con.lpsn.add(lid), fun)
        return [cor_nam for cor_nam in cor_names.values()]

    def __cr_lpsn_id[T](
        self,
        name: str,
        lpsn_id: int,
        get_lpsn: Callable[[int], T],
        eval: Callable[[T], bool],
        /,
    ) -> list[tuple[T, int]]:
        if lpsn_id > 0 and eval(lpsn_val := get_lpsn(lpsn_id)):
            return [(lpsn_val, lpsn_id)]
        return [
            (lpsn_val, lid)
            for _, lid in self.__lpsn.get_name([name])
            if eval(lpsn_val := get_lpsn(lid))
        ]

    def __cr_ncbi_id[T](
        self,
        name: list[str],
        ncbi_id: int,
        get_ncbi: Callable[[int], T],
        eval: Callable[[T], bool],
        /,
    ) -> list[tuple[T, int]]:
        if ncbi_id > 0 and eval(ncbi_val := get_ncbi(ncbi_id)):
            return [(ncbi_val, ncbi_id)]
        return [
            (ncbi_val, nid)
            for _, nid in self._ncbi.get_name(name)
            if eval(ncbi_val := get_ncbi(nid))
        ]

    @_verify_date
    def get_rank(
        self, name: str, ncbi_id: int = -1, lpsn_id: int = -1, /
    ) -> list[RankId]:
        ranks: dict[GBIFRanksE, RankId] = {}

        def fun(rank: GBIFRanksE) -> RankId:
            return RankId(rank=rank)

        cl_name, *_ = self.__prep_name(name)
        ncbi = self.__cr_ncbi_id(
            [cl_name], ncbi_id, self._ncbi.get_rank, is_informative_rank
        )
        lpsn = self.__cr_lpsn_id(
            cl_name, lpsn_id, self.__lpsn.get_rank, is_informative_rank
        )
        _fill_con(ranks, ncbi, lambda con, nid: con.ncbi.add(nid), fun)
        _fill_con(ranks, lpsn, lambda con, lid: con.lpsn.add(lid), fun)
        if len(ranks) > 0:
            return [rank for rank in ranks.values() if _keep_ids(ncbi_id, lpsn_id, rank)]
        return [RankId(rank=self.__gbif.get_rank(cl_name))]

    @_verify_date
    def get_domain(
        self, name: str, ncbi_id: int = -1, lpsn_id: int = -1, /
    ) -> list[DomainId]:
        domains: dict[DomainE, DomainId] = {}

        def fun(dom: DomainE) -> DomainId:
            return DomainId(domain=dom)

        cl_name, *_ = self.__prep_name(name)
        ncbi_res: list[tuple[DomainE, int]] = self.__cr_ncbi_id(
            _create_extra_names_domain(cl_name),
            ncbi_id,
            self._ncbi.get_domain,
            lambda val: val != DomainE.ukn,
        )
        lpsn_res: list[tuple[DomainE, int]] = self.__cr_lpsn_id(
            cl_name, lpsn_id, self.__lpsn.get_domain, lambda val: val != DomainE.ukn
        )

        _fill_con(domains, ncbi_res, lambda con, nid: con.ncbi.add(nid), fun)
        _fill_con(domains, lpsn_res, lambda con, lid: con.lpsn.add(lid), fun)
        if len(domains) > 0:
            return [dom for dom in domains.values() if _keep_ids(ncbi_id, lpsn_id, dom)]
        return []

    @_verify_date
    def get_genus(
        self, name: str, ncbi_id: int = -1, lpsn_id: int = -1, /
    ) -> list[GenusId]:
        genus: dict[str, GenusId] = {}

        def fun(gen: str) -> GenusId:
            return GenusId(genus=gen)

        cl_name, *_ = self.__prep_name(name)
        ncbi: list[tuple[str, int]] = self.__cr_ncbi_id(
            [cl_name], ncbi_id, self._ncbi.get_genus, lambda val: val != ""
        )
        lpsn: list[tuple[str, int]] = self.__cr_lpsn_id(
            cl_name, lpsn_id, self.__lpsn.get_genus, lambda val: val != ""
        )
        _fill_con(genus, ncbi, lambda con, nid: con.ncbi.add(nid), fun)
        _fill_con(genus, lpsn, lambda con, lid: con.lpsn.add(lid), fun)
        if len(genus) > 0:
            return [gen for gen in genus.values() if _keep_ids(ncbi_id, lpsn_id, gen)]
        return []

    @_verify_date
    def get_species(
        self, name: str, ncbi_id: int = -1, lpsn_id: int = -1, /
    ) -> list[SpeciesId]:
        species: dict[str, SpeciesId] = {}

        def fun(spe: str) -> SpeciesId:
            return SpeciesId(species=spe)

        cl_name, *_ = self.__prep_name(name)
        ncbi: list[tuple[str, int]] = self.__cr_ncbi_id(
            [cl_name], ncbi_id, self._ncbi.get_species, lambda val: val != ""
        )
        lpsn: list[tuple[str, int]] = self.__cr_lpsn_id(
            cl_name, lpsn_id, self.__lpsn.get_species, lambda val: val != ""
        )
        _fill_con(species, ncbi, lambda con, nid: con.ncbi.add(nid), fun)
        _fill_con(species, lpsn, lambda con, lid: con.lpsn.add(lid), fun)
        if len(species) > 0:
            return [spe for spe in species.values() if _keep_ids(ncbi_id, lpsn_id, spe)]
        return []

    @_verify_date
    def get_all_species_names(self) -> Iterable[tuple[str, ...]]:
        for _, species_names in self._ncbi.get_all_species():
            yield species_names
        # TODO add lpsn support

    @_verify_date
    def get_all_genus_names(self) -> Iterable[tuple[str, ...]]:
        for _, species_names in self._ncbi.get_all_genera():
            yield species_names
        # TODO add lpsn support

    @_verify_date
    def _init_search_tree(
        self, gen: list[Callable[[], Iterable[tuple[int, tuple[str, ...]]]]]
    ) -> tuple[int, dict[int, str], RadixTree[int]]:
        if self._nid_sg is None or self._radix_sg is None:
            self._nid_sg = dict()
            radix: None | RadixTree[int] = None
            jump = 0
            for nid, names in itertools.chain(*[name() for name in gen]):
                for name in names:
                    if nid not in self._nid_sg:
                        self._nid_sg[nid] = name
                    jump = jump if len(name) < jump else len(name)
                    if radix is None:
                        radix = RadixTree(name, (nid,))
                    else:
                        radix_add(radix, name, (nid,))
            self._radix_sg = radix
            self.__jump = jump
        if self._radix_sg is None:
            raise GlobalManagerEx("Could not initialize taxon radix tree")
        return self.__jump, self._nid_sg, self._radix_sg

    @_verify_date
    def extract_taxa_from_text(self, text: str, /) -> Iterable[str]:
        self._init_search_tree([self._ncbi.get_all_genera, self._ncbi.get_all_species])
        if self._radix_sg is not None and self._nid_sg is not None:
            for rid in extract_taxa_from_text(text, self._radix_sg, self.__jump):
                name = self._nid_sg.get(rid, "")
                if name == "":
                    continue
                yield name

    @_verify_date
    def get_ncbi_id(self, name: str, /) -> list[int]:
        cl_name, *_ = self.__prep_name(name)
        return list(set(nid for _, nid in self._ncbi.get_name([cl_name])))

    @_verify_date
    def patch_ncbi_id(self, ncbi_id: int | None, /) -> int | None:
        if ncbi_id is None or ncbi_id < 1 or self._ncbi.is_deleted(ncbi_id):
            return None
        return self._ncbi.get_correct_id(ncbi_id)

    def patch_lpsn_id(self, lpsn_id: int | None, /) -> int | None:
        if lpsn_id is None or lpsn_id < 1:
            return None
        return self.__lpsn.get_correct_id(lpsn_id)

    def get_lpsn_id(self, name: str, /) -> list[int]:
        cl_name, *_ = self.__prep_name(name)
        return list(set(lid for _, lid in self.__lpsn.get_name([cl_name])))

    def __cr_overlap(
        self, ov_names: Sequence[TaxonName], /
    ) -> tuple[set[str], set[str], set[DomainE]]:
        main_domain: set[DomainE] = set()
        main_genus: set[str] = set()
        main_species: set[str] = set()
        for ov_tax in ov_names:
            patched_lpsn = pa_int(self.patch_lpsn_id(ov_tax.lpsn))
            patched_ncbi = pa_int(self.patch_ncbi_id(ov_tax.ncbi))
            for cr_name in self.get_correct_name(ov_tax.name, patched_ncbi, patched_lpsn):
                main_genus.update(
                    gen.genus
                    for gen in self.get_genus(cr_name.name, patched_ncbi, patched_lpsn)
                )
                main_species.update(
                    spe.species
                    for spe in self.get_species(cr_name.name, patched_ncbi, patched_lpsn)
                )
                main_domain.update(
                    dom.domain
                    for dom in self.get_domain(cr_name.name, patched_ncbi, patched_lpsn)
                )
        return main_species, main_genus, main_domain

    def has_reasonable_taxon_overlap(
        self, name: str, ov_names: Sequence[TaxonName], /
    ) -> TaxonOV:
        if name == "" or len(ov_names) == 0:
            return TaxonOV(fail=True)
        cr_nam = self.get_correct_name(name)
        if len(cr_nam) == 0:
            return TaxonOV(fail=True)
        main_species: set[str] = set(
            spe.species for cnam in cr_nam for spe in self.get_species(cnam.name)
        )
        main_genus: set[str] = set(
            gen.genus for cnam in cr_nam for gen in self.get_genus(cnam.name)
        )
        main_domain: set[DomainE] = set(
            dom.domain for cnam in cr_nam for dom in self.get_domain(cnam.name)
        )
        ov_species, ov_genus, ov_domain = self.__cr_overlap(ov_names)
        return TaxonOV(
            species=len(main_species & ov_species) > 0,
            genus=len(main_genus & ov_genus) > 0,
            domain=len(main_domain & ov_domain) > 0,
            fail=len(main_domain) == 0 or len(ov_domain) == 0,
        )

    @_verify_date
    def get_type_strain(self, ncbi_id: int | None, lpsn_id: int | None, /) -> list[str]:
        return list(
            self._ncbi.get_type_strain(pa_int(ncbi_id))
            | self.__lpsn.get_type_strain(pa_int(lpsn_id))
        )


def slim_init_extractor(
    tax_man: TaxonManager, /
) -> tuple[int, dict[int, str], RadixTree[int]]:
    return tax_man._init_search_tree([tax_man._ncbi.get_all_species])


def slim_extract_taxa_from_text(
    text: str, jump: int, tax_id: dict[int, str], radix: RadixTree[int], /
) -> Iterable[str]:
    if radix is not None and tax_id is not None:
        for rid in extract_taxa_from_text(text, radix, jump):
            name = tax_id.get(rid, "")
            if name == "":
                continue
            yield name
