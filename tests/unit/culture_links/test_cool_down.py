from saim.culture_link.private.cool_down import CoolDownDomain

pytest_plugins = ("tests.fixture.links",)


def test_cool_down(cool_down: CoolDownDomain) -> None:
    assert cool_down is not None
