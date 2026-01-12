from enum import Enum
from typing import Final, final


@final
class CacheNames(str, Enum):
    hom = "homepage"
    cat = "catalogue"
    cat_det = "catalogue_detailed"


@final
class VerificationStatus(str, Enum):
    ok = "OK"
    mis_ele = "CCNo and/or the defined Strings could not be found"
    no_url = "No URL is associated with the BRC"
    timeout = "Request timed out"
    prohibited = "Request was blocked by robots.txt"
    fail_404 = "URL - 404"
    fail_403 = "URL - 403"
    fail_status = "URL - Unpredicted status code"
    err = "An exception was raised"


CAT_EXP_DAYS: Final[int] = 30
CAT_DET_EXP_DAYS: Final[int] = 1
HOME_EXP_DAYS: Final[int] = 60
