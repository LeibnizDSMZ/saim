from typing import Any, Final
import pytest
import re
from saim.designation.extract_ccno import get_ccno_id

from saim.shared.parse.string import clean_string
from saim.shared.error.exceptions import DesignationEx
from saim.shared.data_ops.clean import detect_empty_dict_keys


SAMPLE_IDS: Final[list[str]] = ["1234", "0001", "0000", "B987R"]


def test_clean_string() -> None:
    test_pattern = re.compile(r"\W*")
    assert "" == clean_string("   ", test_pattern)
    assert "T" == clean_string(" T", test_pattern)
    assert "T" == clean_string("T ", test_pattern)
    assert "T" == clean_string(" T ", test_pattern)
    assert "TT" == clean_string(" T T ", test_pattern)


RM_KEY: Final[set[str]] = {
    "empty_string",
    "empty_tuple",
    "empty",
    "empty_list",
    "empty_set",
    "negative_value",
}

TDICT: Final[dict[str, Any]] = {
    "empty_string": "",
    "empty_tuple": (),
    "empty": None,
    "empty_list": [],
    "empty_set": {},
    "negative_value": -1,
    "valid1": 1,
    "valid2": "test",
    "valid3": " ",
}


def test_detect_empty_keys() -> None:
    assert RM_KEY == detect_empty_dict_keys(TDICT)


def test_get_ccno_id() -> None:
    assert "0" == get_ccno_id("DSM 0", "DSM")
    assert "12" == get_ccno_id("DSM12", "DSM")
    assert "123456" == get_ccno_id("DSM     123456", "DSM")
    assert "T33B" == get_ccno_id("DSM T33B", "DSM")
    assert "T33B" == get_ccno_id("DSM-T33B", "DSM")
    assert "%T33B" == get_ccno_id("DSM%T33B", "DSM")

    with pytest.raises(DesignationEx):
        get_ccno_id("DSM", "DSM")

    with pytest.raises(DesignationEx):
        get_ccno_id("DSM 23", "SM")
