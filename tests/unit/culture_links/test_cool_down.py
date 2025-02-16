import pytest
from saim.culture_link.private.cool_down import CoolDownDomain
from saim.shared.error.warnings import RequestWarn

pytest_plugins = ("tests.fixture.links",)


def test_cool_down(cool_down: CoolDownDomain) -> None:
    assert cool_down is not None


def mock_function(x: float) -> tuple[float, bool]:
    if x > 0.5:
        return (0, True)
    return (0, False)


def test_call_after_cool_down(cool_down: CoolDownDomain) -> None:
    with pytest.warns(RequestWarn, match=r"^\[TIMEOUT\] .+ \[0 - 1\] - called$"):
        cool_down.call_after_cool_down(2, mock_function)
    with pytest.warns(RequestWarn, match=r"^\[TIMEOUT\] .+ timeout reset$"):
        cool_down.call_after_cool_down(0.1, mock_function)
