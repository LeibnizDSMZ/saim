import re
from typing import Any, Final

from pydantic import HttpUrl


_LINK: Final[re.Pattern[str]] = re.compile(r"^https?://([^/?]+).*$")


def get_domain(url: str, /) -> str:
    domain = _LINK.match(url)
    if domain is None:
        return ""
    return domain.group(1)


def to_opt_ulr_str(url: Any) -> str | None:
    if isinstance(url, HttpUrl):
        return url.encoded_string()
    if isinstance(url, str):
        return url
    return None
