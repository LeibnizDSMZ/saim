import pytest
from saim.designation.manager import AcronymManager
from saim.shared.error.warnings import StrainMatchWarn
from saim.strain_matching.manager import MatchCache, UpdateResults
from saim.strain_matching.match import match_factory
from saim.strain_matching.private.container import CulMatCon, CultureMatch


pytest_plugins = (
    "tests.fixture.links",
    "tests.fixture.match",
)


def _verify_ccno_match(mat: CulMatCon[CultureMatch]) -> UpdateResults:
    assert mat.strain_id == 1
    assert mat.culture_id == 1
    return UpdateResults(si_id=mat.strain_id, si_cu=mat.culture_id)


def _verify_strain_match(mat: CulMatCon[CultureMatch]) -> UpdateResults:
    assert mat.strain_id == 1
    assert mat.culture_id == -1
    return UpdateResults(si_id=mat.strain_id, si_cu=mat.culture_id)


def _verify_strain_si_id_match(mat: CulMatCon[CultureMatch]) -> UpdateResults:
    assert mat.strain_id == 2
    assert mat.culture_id == -1
    return UpdateResults(si_id=mat.strain_id, si_cu=mat.culture_id)


def _verify_mis_match(mat: CulMatCon[CultureMatch]) -> UpdateResults:
    assert mat.strain_id == -1
    assert mat.culture_id == -1
    return UpdateResults(si_id=mat.strain_id, si_cu=mat.culture_id)


def test_ccno_match(
    acronym_manager: AcronymManager,
    cache_direct_match: MatchCache,
    ccno_dsmz_no_re1: CultureMatch,
) -> None:
    matcher, *_ = match_factory(type(ccno_dsmz_no_re1), False)(
        acronym_manager,
        cache_direct_match,
    )
    res = matcher(ccno_dsmz_no_re1, _verify_ccno_match)
    assert res is None


def test_mis_match(
    acronym_manager: AcronymManager,
    cache_mis_match: MatchCache,
    ccno_dsmz_no_re1: CultureMatch,
) -> None:
    with pytest.warns(StrainMatchWarn):
        matcher, *_ = match_factory(type(ccno_dsmz_no_re1), False)(
            acronym_manager,
            cache_mis_match,
        )
        res = matcher(ccno_dsmz_no_re1, _verify_mis_match)
        assert res is None


def test_ccno_err_match(
    acronym_manager: AcronymManager,
    cache_err_match: MatchCache,
    ccno_dsmz_no_re1: CultureMatch,
) -> None:
    matcher, *_ = match_factory(type(ccno_dsmz_no_re1), False)(
        acronym_manager,
        cache_err_match,
    )
    res = matcher(ccno_dsmz_no_re1, _verify_ccno_match)
    assert res is not None


def test_strain_match(
    acronym_manager: AcronymManager,
    cache_strain_match: MatchCache,
    ccno_dsmz_no_re1: CultureMatch,
) -> None:
    with pytest.warns(StrainMatchWarn):
        matcher, *_ = match_factory(type(ccno_dsmz_no_re1), False)(
            acronym_manager,
            cache_strain_match,
        )
        res = matcher(ccno_dsmz_no_re1, _verify_strain_match)
        assert res is None


def test_strain_rel_si_id_match(
    acronym_manager: AcronymManager,
    cache_strain_match: MatchCache,
    ccno_dsmz_si_id_re1: CultureMatch,
) -> None:
    with pytest.warns(StrainMatchWarn):
        matcher, *_ = match_factory(
            type(ccno_dsmz_si_id_re1),
            False,
        )(
            acronym_manager,
            cache_strain_match,
        )
        res = matcher(ccno_dsmz_si_id_re1, _verify_strain_si_id_match)
        assert res is None


def test_strain_rel_ccno_match(
    acronym_manager: AcronymManager,
    cache_strain_match: MatchCache,
    ccno_dsmz_ccno_re1: CultureMatch,
) -> None:
    with pytest.warns(StrainMatchWarn):
        matcher, *_ = match_factory(type(ccno_dsmz_ccno_re1), False)(
            acronym_manager,
            cache_strain_match,
        )
        res = matcher(ccno_dsmz_ccno_re1, _verify_strain_match)
        assert res is None
