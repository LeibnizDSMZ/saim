from cafi.container.acr_db import CatArgs
from cafi.container.links import CatalogueLink, LinkLevel

from saim.shared.data_con.designation import CCNoDes
from saim.shared.parse.http_url import get_domain


def parse_ccno_to_cat_args(ccno: CCNoDes, /) -> CatArgs:
    return CatArgs(
        acr=ccno.acr,
        id=ccno.id.full,
        pre=ccno.id.pre,
        suf=ccno.id.suf,
        core=ccno.id.core,
    )


def get_domain_from_cafi(links: CatalogueLink, fallback: str, /) -> str:
    match links.level:
        case LinkLevel.cat if len(links.catalogue) > 0:
            return get_domain(links.catalogue[0])
        case LinkLevel.home if fallback == "":
            return get_domain(links.homepage)
        case _:
            return get_domain(fallback)
