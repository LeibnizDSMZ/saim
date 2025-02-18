# we could add whitespace detection for empty strings
from typing import Any, Hashable, Iterable, Mapping, Sized, TypeVar
import unicodedata


_TD = TypeVar("_TD", covariant=True)


def _is_val_empty(val: Any, /) -> bool:
    if isinstance(val, Sized) and len(val) == 0:
        return True
    if isinstance(val, int) and val < 0:
        return True
    if val is None:
        return True
    return False


def detect_empty_dict_keys(dict_con: Mapping[str, Any], /) -> set[str]:
    to_rem = set()
    for key, val in dict_con.items():
        if _is_val_empty(val):
            to_rem.add(key)
    return to_rem


def clean_empty_values_in_dict(dict_con: dict[str, _TD], /) -> dict[str, _TD]:
    trim: dict[str, _TD] = trim_str_in_dict(dict_con)

    def _select_rec(val: Any, /) -> Any:
        if isinstance(val, dict):
            return _rec_clean_dic(val)
        if isinstance(val, (list, tuple)):
            return _rec_clean_ite(val)
        return val

    def _rec_clean_ite(local_l: Iterable[Any], /) -> Iterable[Any]:
        gen = (new_v for val in local_l if not _is_val_empty(new_v := _select_rec(val)))
        if isinstance(local_l, tuple):
            return tuple(gen)
        return list(gen)

    def _rec_clean_dic(local_d: dict[str, Any], /) -> dict[str, Any]:
        buf = {key: _select_rec(val) for key, val in local_d.items()}
        banned = detect_empty_dict_keys(buf)
        return {key: val for key, val in buf.items() if key not in banned}

    return _rec_clean_dic(trim)


def is_different_string(strict: bool, str_1: str, str_2: str, /) -> bool:
    if not strict:
        str_1, str_2 = str_1.upper(), str_2.upper()
    return str_1 != str_2


def trim_str_in_dict(dict_con: dict[str, _TD], /) -> dict[str, _TD]:
    new_dict: dict[str, _TD] = {}

    def _trim_string(val: Any) -> Any:
        if isinstance(val, str):
            return unicodedata.normalize("NFKD", val.strip())
        return val

    for key, val in dict_con.items():
        new_val = _trim_string(val)
        if isinstance(val, list):
            new_val = [_trim_string(ele) for ele in val]
        if isinstance(val, set):
            new_val = set(_trim_string(ele) for ele in val)
        new_dict[key] = new_val
    return new_dict


def has_duplicates(data: Iterable[Hashable], /) -> bool:
    buf = set()
    for ele in data:
        if ele in buf:
            return True
        buf.add(ele)
    return False


def filter_duplicates[T: Hashable](data: Iterable[T], /) -> Iterable[T]:
    buf = set()
    for ele in data:
        if ele not in buf:
            yield ele
        buf.add(ele)
