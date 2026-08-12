import re
from typing import Any

from saim.shared.parse.string import (
    PATTERN_REDUNDANT_SPACE_R,
    clean_ledge_rm_tags,
    clean_string,
)


_UND = re.compile(r"_+")


def fix_taxa_name(source: Any) -> str:
    if not isinstance(source, str):
        return ""
    clean = clean_ledge_rm_tags(source)
    if " " not in clean:
        clean = _UND.sub(" ", clean)
    clean = clean_string(clean, PATTERN_REDUNDANT_SPACE_R)
    if len(clean) > 1:
        return clean[0].upper() + clean[1:]
    return clean
