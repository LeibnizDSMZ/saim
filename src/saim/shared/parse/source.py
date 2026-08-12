from typing import Any

from saim.shared.parse.string import clean_text_rm_tags


def fix_source(source: Any) -> str:
    if not isinstance(source, str):
        return ""
    clean = clean_text_rm_tags(source)
    if len(clean) > 1:
        return clean[0].upper() + clean[1:]
    return clean
