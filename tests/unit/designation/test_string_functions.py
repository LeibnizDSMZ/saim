import re

from saim.shared.parse.string import (
    clean_string,
    replace_non_word_chars,
)


def test_clean_string_nothing() -> None:
    test_string = "-Hello- #"
    test_pattern = re.compile(r"")
    assert clean_string(test_string, test_pattern) == "-Hello- #"


def test_clean_string_clean() -> None:
    test_string = "-Hello- #"
    test_pattern = re.compile(r"\W")
    assert clean_string(test_string, test_pattern) == "Hello"


def test_clean_string_multipatterns() -> None:
    test_string = "-Hello12 - 3World 45 #"
    test_pattern = re.compile(r"\W")
    test_pattern_num = re.compile(r"\d")
    assert clean_string(test_string, test_pattern) == "Hello123World45"
    assert clean_string(test_string, test_pattern, test_pattern_num) == "HelloWorld"


def test_replace_non_word_chars() -> None:
    assert replace_non_word_chars("Test-") == "Test:"
    assert replace_non_word_chars("-Test") == ":Test"
    assert replace_non_word_chars("-Test-") == ":Test:"
    assert replace_non_word_chars("---Test---") == ":Test:"
