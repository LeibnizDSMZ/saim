import re
from saim.shared.data_con.designation import STRAIN_SI_ID_DOI


_REG_DOI = re.compile(r"(?i)^10\.\d{4,9}/\S+$")


def check_si_id_doi(doi: str, /) -> str:
    if STRAIN_SI_ID_DOI.match(doi) is not None:
        return doi
    raise ValueError(f"DOI {doi} has an invalid StrainInfo format")


def is_correct_doi(doi: str, /) -> bool:
    return _REG_DOI.match(doi) is not None
