import re
from re import Pattern
from typing import Final


# https://www.ddbj.nig.ac.jp/documents/accessions-e.html
# https://www.ncbi.nlm.nih.gov/genbank/acc_prefix/
# https://support.nlm.nih.gov/knowledgebase/article/KA-03434/en-us

_ASSE_CORE: Final[str] = (
    # GENBANK + REFSEQ assemblies
    r"(?:GCA_|GCF_)\d+"
    +
    # WGS + TSA + TLS
    r"|[A-Z]{4}\d{8,}|[A-Z]{6}\d{9,}"
    +
    # MGA - Mass sequence for Genome Annotation
    # (DDBJ terminated accepting new submission of MGA data)
    r"|[A-Z]{5}\d{7}"
)

_ACC_ASSE: Final[str] = r"(" + _ASSE_CORE + r")(?:\.d+)?"

_NUC_CORE: Final[str] = (
    # Nucleotide
    r"[A-Z]\d{5}|[A-Z]{2}\d{6}|[A-Z]{2}\d{8}"
    +
    # RefSeq - dna/rna only
    r"|(?:AC_|NC_|NG_|NT_|NW_|NZ_|NM_|NR_|XM_|XR_)\d+"
)

_ACC_NUC: Final[str] = r"(" + _NUC_CORE + r")(?:\.d+)?"


_ACC_ALL: Final[str] = r"(" + _ASSE_CORE + "|" + _NUC_CORE + r")(?:\.d+)?"

_ACC_REG: Final[Pattern[str]] = re.compile(_ACC_ALL)
_IS_ACC: Final[Pattern[str]] = re.compile(r"^" + _ACC_ALL + r"$")


_IS_ACC_N: Final[Pattern[str]] = re.compile(r"^" + _ACC_NUC + r"$")
_IS_ACC_A: Final[Pattern[str]] = re.compile(r"^" + _ACC_ASSE + r"$")


def is_acc(acc: str, /) -> bool:
    return _IS_ACC.match(acc) is not None


def get_is_acc_regex() -> str:
    return rf"^{_ACC_ALL}$"


def is_assembly(acc: str, /) -> bool:
    return _IS_ACC_A.match(acc) is not None


def is_nucleotide(acc: str, /) -> bool:
    return _IS_ACC_N.match(acc) is not None


def _sep_seq_str(acc: str, /) -> set[str]:
    return {mat.group(1) for mat in _ACC_REG.finditer(acc)}


def parse_seq_acc(to_parse: str, /) -> set[str]:
    acc_res = _sep_seq_str(to_parse)
    if len(acc_res) == 0:
        return set()
    return acc_res


def check_sequence(acc: str, /) -> str:
    if is_acc(acc):
        return acc
    raise ValueError(f"{acc} is not a valid sequence accession number")
