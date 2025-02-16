from saim.shared.data_con.designation import STRAIN_SI_ID_DOI


def check_si_id_doi(doi: str, /) -> str:
    if STRAIN_SI_ID_DOI.match(doi) is not None:
        return doi
    raise ValueError(f"DOI {doi} has an invalid StrainInfo format")
