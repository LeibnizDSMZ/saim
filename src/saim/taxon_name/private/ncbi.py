from collections import defaultdict
from enum import Enum
from io import BytesIO
from pathlib import Path
from re import Pattern
import re
import tarfile
from typing import IO, Callable, Final, Iterable, final
import warnings


from saim.shared.cache.request import create_simple_get_cache, create_sqlite_backend
from saim.shared.data_con.taxon import (
    DomainE,
    GBIFRanksE,
    has_virus_in_name,
    is_domain,
    is_ncbi_rank,
    is_rank,
    parse_domain,
    parse_ncbi_rank,
)
from saim.shared.error.exceptions import RequestURIEx, ValidationEx
from saim.shared.error.warnings import TaxonWarn
from saim.taxon_name.private.container import NcbiTaxCon


_FIELD_TAX_TERM: Final[str] = "\t|\t"
_ROW_TAX_TERM: Final[str] = "\t|\n"


class _NameClass(str, Enum):
    nam = "scientific name"
    syn = "synonym"
    tst = "type material"
    eq_nam = "equivalent name"


_NAMES_REG: Final[Pattern[str]] = re.compile(
    r"^" + r"\s*\|\s*".join(["1", "all", r"\s", "synonym"]) + r"(\s*\|.*)?$"
)
_MERGED_REG: Final[Pattern[str]] = re.compile(r"^\s*\d+\s*\|\s*\d+\s*(\|.*)?$")
_DEL_REG: Final[Pattern[str]] = re.compile(r"^\s*\d+\s*(\|.*)?$")
_SPE_FL = re.compile(r"sp\.")

_NCBI_NAMES = tuple[
    dict[str, set[int]],
    dict[str, set[int]],
    dict[str, set[int]],
    dict[int, set[str]],
    dict[int, str],
]


def read_ncbi_tax_names(
    tax_csv: IO[bytes], ranks: dict[int, GBIFRanksE], /
) -> _NCBI_NAMES:
    syns: dict[str, set[int]] = defaultdict(set)
    names: dict[str, set[int]] = defaultdict(set)
    eq_nam: dict[str, set[int]] = defaultdict(set)
    t_str: dict[int, set[str]] = defaultdict(set)
    id2nam: dict[int, str] = {}
    for ind, line in enumerate(tax_csv):
        line_dec = line.decode("utf-8")
        if ind == 0 and _NAMES_REG.match(line_dec) is None:
            raise ValidationEx("Names tax file is malformed!")
        nid, name, _, cla = line_dec.strip(_ROW_TAX_TERM).split(_FIELD_TAX_TERM)
        nid_int = int(nid)
        if nid_int in ranks:
            match cla:
                case str(_NameClass.nam.value):
                    names[name].add(nid_int)
                    id2nam[nid_int] = name
                case str(_NameClass.syn.value):
                    syns[name].add(nid_int)
                case str(_NameClass.eq_nam.value):
                    eq_nam[name].add(nid_int)
                case str(_NameClass.tst.value):
                    t_str[nid_int].add(name)
    return (names, eq_nam, syns, t_str, id2nam)


def read_ncbi_tax_merged(tax_csv: IO[bytes], /) -> dict[int, int]:
    mer_ids: dict[int, int] = {}
    for line in tax_csv:
        line_dec = line.decode("utf-8")
        if _MERGED_REG.match(line_dec) is None:
            raise ValidationEx("Merged tax file is malformed!")
        old_id, new_id, *_ = line_dec.strip(_ROW_TAX_TERM).split(_FIELD_TAX_TERM)
        mer_ids[int(old_id)] = int(new_id)
    return mer_ids


def read_ncbi_tax_deleted(tax_csv: IO[bytes], /) -> set[int]:
    del_ids: set[int] = set()
    for line in tax_csv:
        line_dec = line.decode("utf-8")
        if _DEL_REG.match(line_dec) is None:
            raise ValidationEx("Deleted tax file is malformed!")
        del_id, *_ = line_dec.strip(_ROW_TAX_TERM).split(_FIELD_TAX_TERM)
        del_ids.add(int(del_id))
    return del_ids


def _resolve_rank(
    cur_id: int, ranks: dict[int, GBIFRanksE], path: dict[int, int], limit: GBIFRanksE, /
) -> int | None:
    if path.get(cur_id, cur_id) == cur_id:
        return None
    if ranks.get(cur_id) == limit:
        return cur_id
    return _resolve_rank(path[cur_id], ranks, path, limit)


def _create_all_correct_names(
    con: dict[int, int], id_2_name: dict[int, str], /
) -> dict[int, tuple[str, ...]]:
    cor_spe: dict[int, tuple[str, ...]] = {}
    for spe_id in con.values():
        cor_name = id_2_name.get(spe_id, "")
        if cor_name == "" or _SPE_FL.search(cor_name) is not None:
            continue
        cor_spe[spe_id] = (cor_name, *cor_spe.get(spe_id, tuple()))
    return cor_spe


def _add_synonyms_to_names(
    all_names: dict[int, tuple[str, ...]], synonyms: dict[str, set[int]], /
) -> None:
    for name, ids in synonyms.items():
        if name == "" or _SPE_FL.search(name) is not None:
            continue
        for nid in ids:
            if nid not in all_names:
                continue
            all_names[nid] = (*all_names.get(nid, tuple()), name)


_NODE_REG: Final[Pattern[str]] = re.compile(
    r"^" + r"\s*\|\s*".join(["1", "1", "no rank"]) + r"\s*\|.*$"
)


def read_ncbi_tax_nodes(
    tax_csv: IO[bytes], /
) -> tuple[dict[int, GBIFRanksE], dict[int, int], dict[int, int], dict[int, int]]:
    ranks: dict[int, GBIFRanksE] = {}
    path: dict[int, int] = {}
    for ind, line in enumerate(tax_csv):
        line_dec = line.decode("utf-8")
        if ind == 0 and _NODE_REG.match(line_dec) is None:
            raise ValidationEx("Node tax file is malformed!")
        rank: str
        tax_id, parent, rank, *_ = line_dec.strip(_ROW_TAX_TERM).split(_FIELD_TAX_TERM)
        tax_id_int = int(tax_id)
        path[tax_id_int] = int(parent)
        rank = rank.upper()
        if is_rank(rank) or is_ncbi_rank(rank):
            ranks[tax_id_int] = parse_ncbi_rank(rank)
        else:
            warnings.warn(f"{rank} - unknown!", TaxonWarn, stacklevel=2)
    return (
        ranks,
        {
            tid: gid
            for tid in ranks
            if (gid := _resolve_rank(tid, ranks, path, GBIFRanksE.dom)) is not None
        },
        {
            tid: gid
            for tid in ranks
            if (gid := _resolve_rank(tid, ranks, path, GBIFRanksE.gen)) is not None
        },
        {
            tid: gid
            for tid in ranks
            if (gid := _resolve_rank(tid, ranks, path, GBIFRanksE.spe)) is not None
        },
    )


_NCBI_FTP: Final[str] = "https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz"
_CLEAN: Final[tuple[Pattern[str], ...]] = (re.compile(r"^culture-collection:\s+"),)


def clean_ncbi_strain(strain: str, /) -> str:
    clean = strain
    for sub in _CLEAN:
        clean = sub.sub("", clean)
    return clean


def find_ncbi_name(name: str, names: NcbiTaxCon, /) -> tuple[set[int], str] | None:
    if name == "":
        return None
    if (f_nam := names.name.get(name, None)) is not None:
        return f_nam, name
    if (f_nam := names.eq_name.get(name, None)) is not None:
        return f_nam, name
    if (f_nam_l := names.synonyms.get(name, None)) is not None:
        return f_nam_l, name
    return None


def _create_all_names(names: list[str], /) -> list[str]:
    new_names = [name for name in names if name != ""]
    if not any(has_virus_in_name(name) for name in names):
        new_names.extend(f"{name} virus" for name in names)
    return new_names


def _first_correct_name(
    ncbi_tax: NcbiTaxCon, names: list[str], /
) -> list[tuple[str, int]]:
    for tax_name in _create_all_names(names):
        name_id = find_ncbi_name(tax_name, ncbi_tax)
        if name_id is not None:
            return [(name_id[1], nid) for nid in name_id[0]]
    return []


_NCBI_TAR = tuple[
    tarfile.TarInfo | None,
    dict[int, GBIFRanksE],
    dict[int, int],
    dict[int, int],
    dict[int, int],
    dict[int, int],
    set[int],
]


def _extract_from_file(tar: tarfile.TarFile, /) -> _NCBI_TAR:
    to_read_main: None | tarfile.TarInfo = None
    ranks: dict[int, GBIFRanksE] = {}
    domain: dict[int, int] = {}
    genus: dict[int, int] = {}
    species: dict[int, int] = {}
    del_nodes: set[int] = set()
    merged: dict[int, int] = {}
    for member in tar.getmembers():
        match member.name:
            case "names.dmp":
                to_read_main = member
            case "nodes.dmp" if (ext_res := tar.extractfile(member)) is not None:
                ranks, domain, genus, species = read_ncbi_tax_nodes(ext_res)
            case "merged.dmp" if (ext_res := tar.extractfile(member)) is not None:
                merged = read_ncbi_tax_merged(ext_res)
            case "delnodes.dmp" if (ext_res := tar.extractfile(member)) is not None:
                del_nodes = read_ncbi_tax_deleted(ext_res)
    return to_read_main, ranks, domain, genus, species, merged, del_nodes


def _create_ncbi_container(res_down: bytes, /) -> NcbiTaxCon | None:
    ran: dict[int, GBIFRanksE] = {}
    dom: dict[int, int] = {}
    gen: dict[int, int] = {}
    spec: dict[int, int] = {}
    mer: dict[int, int] = {}
    rm_nod: set[int] = set()
    main, ro_main = None, None
    with tarfile.open(fileobj=BytesIO(res_down), mode="r:gz") as tar:
        ro_main, ran, dom, gen, spec, mer, rm_nod = _extract_from_file(tar)
        if not (ro_main is None or (ext_res := tar.extractfile(ro_main)) is None):
            names, eqn, syns, t_str, id2n = read_ncbi_tax_names(ext_res, ran)
            main = NcbiTaxCon(
                name=names,
                eq_name=eqn,
                synonyms=syns,
                type_str=t_str,
                id_2_name=id2n,
                rank=ran,
                domain=dom,
                genus=gen,
                species=spec,
                map_ids=mer,
                rm_ids=rm_nod,
            )
    return main


def _patch_ncbi_id[
    T
](func: Callable[["NcbiTaxReq", int], T]) -> Callable[["NcbiTaxReq", int | None], T]:
    def wrap(self: "NcbiTaxReq", ncbi_id: int | None) -> T:
        ncbi_p = self.get_correct_id(ncbi_id)
        if ncbi_p is None:
            return func(self, -1)
        return func(self, ncbi_p)

    return wrap


@final
class NcbiTaxReq:
    __slots__ = ("__backend", "__con", "__exp_days")

    def __init__(self, work_dir: Path, exp_days: int, delete: bool = False, /) -> None:
        self.__exp_days = exp_days
        file = "taxon_name_ncbi"
        if delete:
            work_dir.joinpath(file).unlink(True)
        self.__backend = create_sqlite_backend(file, work_dir)(10, self.__exp_days)
        self.__con = self.__download()
        super().__init__()

    def __download(self) -> NcbiTaxCon:
        with create_simple_get_cache(self.__exp_days, self.__backend) as session:
            res = session.get(_NCBI_FTP, stream=True, timeout=60)
            if res.status_code == 200:
                print(f"Downloading {_NCBI_FTP} - cache [{res.from_cache}]")
                res_down = res.content
            else:
                raise RequestURIEx(f"Could not get {_NCBI_FTP}")
            main = _create_ncbi_container(res_down)
            if main is not None:
                return main
        raise RequestURIEx("Could not create container for NCBI taxonomy")

    def get_name(self, names: list[str], /) -> list[tuple[str, int]]:
        return _first_correct_name(self.__con, names)

    def get_correct_name(self, name: str, ncbi_id: int = -1, /) -> list[tuple[str, int]]:
        ncbi_p = self.get_correct_id(ncbi_id)
        if (
            ncbi_p is not None
            and (cor_name := self.__con.id_2_name.get(ncbi_p, "")) != ""
        ):
            return [(cor_name, ncbi_p)]
        name_id = self.get_name([name])
        if len(name_id) == 0:
            return []
        return [
            (cor_name, nid)
            for _, nid in name_id
            if (cor_name := self.__con.id_2_name.get(nid, "")) != ""
        ]

    @_patch_ncbi_id
    def get_rank(self, ncbi_id: int, /) -> GBIFRanksE:
        if ncbi_id < 1:
            return GBIFRanksE.oth
        return self.__con.rank.get(ncbi_id, GBIFRanksE.oth)

    @_patch_ncbi_id
    def get_domain(self, ncbi_id: int, /) -> DomainE:
        if ncbi_id < 1:
            return DomainE.ukn
        domain_id = self.__con.domain.get(ncbi_id, None)
        if domain_id is None:
            return DomainE.ukn
        domain_name = self.__con.id_2_name.get(domain_id, "").upper()
        if not is_domain(domain_name):
            return DomainE.ukn
        return parse_domain(domain_name)

    @_patch_ncbi_id
    def get_genus(self, ncbi_id: int, /) -> str:
        if ncbi_id < 1:
            return ""
        genus_id = self.__con.genus.get(ncbi_id, None)
        if genus_id is None:
            return ""
        return self.__con.id_2_name.get(genus_id, "").upper()

    @_patch_ncbi_id
    def get_species(self, ncbi_id: int, /) -> str:
        if ncbi_id < 1:
            return ""
        species_id = self.__con.species.get(ncbi_id, None)
        if species_id is None:
            return ""
        return self.__con.id_2_name.get(species_id, "").upper()

    def get_all_species(self) -> Iterable[tuple[int, tuple[str, ...]]]:
        all_spe = _create_all_correct_names(self.__con.species, self.__con.id_2_name)
        _add_synonyms_to_names(all_spe, self.__con.synonyms)
        _add_synonyms_to_names(all_spe, self.__con.eq_name)
        for nid, names in all_spe.items():
            if len(names) == 0:
                continue
            yield nid, names

    def get_all_genera(self) -> Iterable[tuple[int, tuple[str, ...]]]:
        all_spe = _create_all_correct_names(self.__con.genus, self.__con.id_2_name)
        _add_synonyms_to_names(all_spe, self.__con.synonyms)
        _add_synonyms_to_names(all_spe, self.__con.eq_name)
        for nid, names in all_spe.items():
            if len(names) == 0:
                continue
            yield nid, names

    def is_deleted(self, ncbi_id: int, /) -> bool:
        return ncbi_id in self.__con.rm_ids

    def get_correct_id(self, ncbi_id: int | None, /) -> int | None:
        if ncbi_id is None or ncbi_id < 1:
            return None
        merged_id = self.__con.map_ids.get(ncbi_id, None)
        if merged_id is not None and merged_id in self.__con.id_2_name:
            return merged_id
        if ncbi_id in self.__con.id_2_name:
            return ncbi_id
        return None

    @_patch_ncbi_id
    def get_type_strain(self, ncbi_id: int, /) -> set[str]:
        if ncbi_id < 1:
            return set()
        return self.__con.type_str.get(ncbi_id, set())
