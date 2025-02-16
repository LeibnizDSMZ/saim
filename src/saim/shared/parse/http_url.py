import re
from typing import Final


_LINK: Final[re.Pattern[str]] = re.compile(r"^https?://([^/?]+).*$")


def get_domain(url: str, /) -> str:
    domain = _LINK.match(url)
    if domain is None:
        return ""
    return domain.group(1)
