from enum import Enum
from re import Pattern
import re
from typing import Final
from typing import final


@final
class GBIFTypeE(str, Enum):
    vir = "VIRUS"
    sci = "SCIENTIFIC"
    hyb = "HYBRID"
    inf = "INFORMAL"
    culp = "CULTIVAR"
    can = "CANDIDATUS"
    dou = "DOUBTFUL"
    pla = "PLACEHOLDER"
    non = "NO_NAME"
    blk = "BLACKLISTED"
    otu = "OTU"


@final
class GBIFRanksE(str, Enum):
    dom = "DOMAIN"
    sup_kin = "SUPERKINGDOM"
    kin = "KINGDOM"
    sub_kin = "SUBKINGDOM"
    inf_kin = "INFRAKINGDOM"
    sup_pyl = "SUPERPHYLUM"
    pyl = "PHYLUM"
    sub_pyl = "SUBPHYLUM"
    inf_pyl = "INFRAPHYLUM"
    sup_cla = "SUPERCLASS"
    cla = "CLASS"
    sub_cla = "SUBCLASS"
    inf_cla = "INFRACLASS"
    par_cla = "PARVCLASS"
    sup_leg = "SUPERLEGION"
    leg = "LEGION"
    sub_leg = "SUBLEGION"
    inf_leg = "INFRALEGION"
    sup_coh = "SUPERCOHORT"
    coh = "COHORT"
    sub_coh = "SUBCOHORT"
    inf_coh = "INFRACOHORT"
    mag_ord = "MAGNORDER"
    sup_ord = "SUPERORDER"
    gra_ord = "GRANDORDER"
    ord = "ORDER"
    sub_ord = "SUBORDER"
    inf_ord = "INFRAORDER"
    par_ord = "PARVORDER"
    sup_fam = "SUPERFAMILY"
    fam = "FAMILY"
    sub_fam = "SUBFAMILY"
    inf_fam = "INFRAFAMILY"
    sup_tri = "SUPERTRIBE"
    tri = "TRIBE"
    sub_tri = "SUBTRIBE"
    inf_tri = "INFRATRIBE"
    sup_genc = "SUPRAGENERIC_NAME"
    gen = "GENUS"
    sub_gen = "SUBGENUS"
    inf_gen = "INFRAGENUS"
    sec = "SECTION"
    sub_sec = "SUBSECTION"
    seri = "SERIES"
    sub_ser = "SUBSERIES"
    inf_genc = "INFRAGENERIC_NAME"
    agg = "SPECIES_AGGREGATE"
    spe = "SPECIES"
    inf_spec = "INFRASPECIFIC_NAME"
    grex = "GREX"
    sub_spe = "SUBSPECIES"
    cul_var_gr = "CULTIVAR_GROUP"
    con_var = "CONVARIETY"  # legacy
    inf_sub_spec = "INFRASUBSPECIFIC_NAME"
    prol = "PROLES"  # legacy
    rac = "RACE"  # legacy
    nat = "NATIO"  # legacy
    abe = "ABERRATION"  # legacy
    morph = "MORPH"  # legacy
    var = "VARIETY"
    sub_var = "SUBVARIETY"
    form = "FORM"
    sub_form = "SUBFORM"
    pat_var = "PATHOVAR"
    bio_var = "BIOVAR"
    che_var = "CHEMOVAR"
    mor_var = "MORPHOVAR"
    pha_var = "PHAGOVAR"
    ser_var = "SEROVAR"
    che_form = "CHEMOFORM"
    for_spec = "FORMA_SPECIALIS"
    cul_var = "CULTIVAR"
    str = "STRAIN"
    oth = "OTHER"
    unr = "UNRANKED"


_ORG_RANKS_GBIF: Final[dict[str, GBIFRanksE]] = {
    "dom.": GBIFRanksE.dom,
    "superreg.": GBIFRanksE.sup_kin,
    "reg.": GBIFRanksE.kin,
    "subreg.": GBIFRanksE.sub_kin,
    "infrareg.": GBIFRanksE.inf_kin,
    "superphyl.": GBIFRanksE.sup_pyl,
    "phyl.": GBIFRanksE.pyl,
    "subphyl.": GBIFRanksE.sub_pyl,
    "infraphyl.": GBIFRanksE.inf_pyl,
    "supercl.": GBIFRanksE.sup_cla,
    "cl.": GBIFRanksE.cla,
    "subcl.": GBIFRanksE.sub_cla,
    "infracl.": GBIFRanksE.inf_cla,
    "parvcl.": GBIFRanksE.par_cla,
    "superleg.": GBIFRanksE.sup_leg,
    "leg.": GBIFRanksE.leg,
    "subleg.": GBIFRanksE.sub_leg,
    "infraleg.": GBIFRanksE.inf_leg,
    "supercohort": GBIFRanksE.sup_coh,
    "cohort": GBIFRanksE.coh,
    "subcohort": GBIFRanksE.sub_coh,
    "infracohort": GBIFRanksE.inf_coh,
    "magnord.": GBIFRanksE.mag_ord,
    "superord.": GBIFRanksE.sup_ord,
    "grandord.": GBIFRanksE.gra_ord,
    "ord.": GBIFRanksE.ord,
    "subord.": GBIFRanksE.sub_ord,
    "infraord.": GBIFRanksE.inf_ord,
    "parvord.": GBIFRanksE.par_ord,
    "superfam.": GBIFRanksE.sup_fam,
    "fam.": GBIFRanksE.fam,
    "subfam.": GBIFRanksE.sub_fam,
    "infrafam.": GBIFRanksE.inf_fam,
    "supertrib.": GBIFRanksE.sup_tri,
    "trib.": GBIFRanksE.tri,
    "subtrib.": GBIFRanksE.sub_tri,
    "infratrib.": GBIFRanksE.inf_tri,
    "supragen.": GBIFRanksE.sup_genc,
    "gen.": GBIFRanksE.gen,
    "subgen.": GBIFRanksE.sub_gen,
    "infragen.": GBIFRanksE.inf_gen,
    "sect.": GBIFRanksE.sec,
    "subsect.": GBIFRanksE.sub_sec,
    "ser.": GBIFRanksE.seri,
    "subser.": GBIFRanksE.sub_ser,
    "infrageneric": GBIFRanksE.inf_genc,
    "agg.": GBIFRanksE.agg,
    "sp.": GBIFRanksE.spe,
    "infrasp.": GBIFRanksE.inf_spec,
    "grex": GBIFRanksE.grex,
    "subsp.": GBIFRanksE.sub_spe,
    "cultivar group": GBIFRanksE.cul_var_gr,
    "convar.": GBIFRanksE.con_var,
    "infrasubsp.": GBIFRanksE.inf_sub_spec,
    "prol.": GBIFRanksE.prol,
    "race": GBIFRanksE.rac,
    "natio": GBIFRanksE.nat,
    "ab.": GBIFRanksE.abe,
    "morph": GBIFRanksE.morph,
    "var.": GBIFRanksE.var,
    "subvar.": GBIFRanksE.sub_var,
    "f.": GBIFRanksE.form,
    "subf.": GBIFRanksE.sub_form,
    "pv.": GBIFRanksE.pat_var,
    "biovar": GBIFRanksE.bio_var,
    "chemovar": GBIFRanksE.che_var,
    "morphovar": GBIFRanksE.mor_var,
    "phagovar": GBIFRanksE.pha_var,
    "serovar": GBIFRanksE.ser_var,
    "chemoform": GBIFRanksE.che_form,
    "f.sp.": GBIFRanksE.for_spec,
    "cv.": GBIFRanksE.cul_var,
    "strain": GBIFRanksE.str,
    "other": GBIFRanksE.oth,
    "unranked": GBIFRanksE.unr,
}

_NCBI_EXCLUSIVE_RANKS_MAP: Final[dict[str, GBIFRanksE]] = {
    "FORMA SPECIALIS": GBIFRanksE.for_spec,
    "PATHOGROUP": GBIFRanksE.oth,
    "VARIETAS": GBIFRanksE.var,
    "SPECIES GROUP": GBIFRanksE.oth,
    "SPECIES SUBGROUP": GBIFRanksE.oth,
    "GENOTYPE": GBIFRanksE.oth,
    "ISOLATE": GBIFRanksE.oth,
    "SEROGROUP": GBIFRanksE.oth,
    "SEROTYPE": GBIFRanksE.ser_var,
    "FORMA": GBIFRanksE.form,
    "BIOTYPE": GBIFRanksE.oth,
    "CLADE": GBIFRanksE.oth,
    "NO RANK": GBIFRanksE.unr,
}


@final
class DomainE(str, Enum):
    ukn = "UNKNOWN"
    bac = "BACTERIA"
    arc = "ARCHAEA"
    euk = "EUKARYOTA"
    vir = "VIRUSES"


_L_RANKS: Final[set[str]] = {str(rank.value) for rank in GBIFRanksE}
_L_RANKS_MAP: Final[dict[str, GBIFRanksE]] = {
    str(rank.value): rank for rank in GBIFRanksE
}
_L_NCBI_RANKS: Final[set[str]] = set(_NCBI_EXCLUSIVE_RANKS_MAP.keys())
_L_DOMAIN: Final[set[str]] = {str(ski.value) for ski in DomainE}
_L_DOMAIN_MAP: Final[dict[str, DomainE]] = {str(ski.value): ski for ski in DomainE}
_L_GBIF_TYP: Final[set[str]] = {str(typ.value) for typ in GBIFTypeE}


def get_ranks_list() -> list[str]:
    return list(_L_RANKS)


def get_ranks_abr_list() -> list[str]:
    return list(_ORG_RANKS_GBIF.keys())


def get_domain_list() -> list[str]:
    return list(_L_DOMAIN)


def get_gbif_types() -> list[str]:
    return list(_L_GBIF_TYP)


_GEN_RANKS: Final[set[GBIFRanksE]] = {
    GBIFRanksE.unr,
    GBIFRanksE.oth,
}


def is_rank(name: str, /) -> bool:
    return name in _L_RANKS


def is_ncbi_rank(name: str, /) -> bool:
    return name in _L_NCBI_RANKS


def parse_ncbi_rank(name: str, /) -> GBIFRanksE:
    return _NCBI_EXCLUSIVE_RANKS_MAP.get(name, _L_RANKS_MAP.get(name, GBIFRanksE.oth))


def is_informative_rank(name: GBIFRanksE, /) -> bool:
    return name not in _GEN_RANKS


def is_domain(name: str, /) -> bool:
    return name in _L_DOMAIN


def parse_domain(name: str, /) -> DomainE:
    return _L_DOMAIN_MAP.get(name, DomainE.ukn)


def parse_gbif_rank(name: str, /) -> GBIFRanksE:
    return _ORG_RANKS_GBIF.get(name, GBIFRanksE.oth)


def parse_rank(name: str, /) -> GBIFRanksE:
    return _L_RANKS_MAP.get(name, GBIFRanksE.oth)


_VIRUS_REG: Final[tuple[Pattern[str], ...]] = (
    re.compile(r"[a-z\s]virus($|\s)"),
    re.compile(r"\sphage($|\s)"),
)


def has_virus_in_name(name: str, /) -> bool:
    for reg in _VIRUS_REG:
        if reg.search(name) is not None:
            return True
    return False
