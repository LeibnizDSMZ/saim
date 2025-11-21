from dataclasses import dataclass, field
import pytest

from saim.designation.manager import AcronymManager
from saim.shared.data_con.designation import CCNoId
from saim.shared.data_con.deposit import DepositStatus
from saim.shared.data_con.strain import StrainDepositId
from saim.strain_matching.manager import MatchCache

from cafi.constants.versions import CURRENT_VER


@dataclass
class _TestStrain:
    relation: list[str] = field(default_factory=list)
    strain_id = -1


@dataclass
class _TestCCNo:
    ccno: str
    acr: str
    brc_id: int
    id: CCNoId
    id_syn: list[CCNoId]
    status: DepositStatus
    strain: _TestStrain


@pytest.fixture
def relation_cache_1() -> dict[tuple[str, str, str, str], dict[int, int]]:
    return {("DSM", "", "112721", ""): {1: 1}}


@pytest.fixture
def deposit_ccno_1() -> dict[tuple[int, str, str, str], StrainDepositId]:
    return {(1, "", "112721", ""): StrainDepositId(c=1, s=1)}


@pytest.fixture
def si_dp_err_1() -> set[int]:
    return {1}


@pytest.fixture
def si_id_1() -> dict[int, int]:
    return {1: 1, 2: 2}


@pytest.fixture
def ccno_dsmz_no_re1() -> _TestCCNo:
    return _TestCCNo(
        "DSM 112721",
        "DSM",
        1,
        CCNoId(full="112721", core="112721"),
        [],
        DepositStatus.unk,
        _TestStrain(),
    )


@pytest.fixture
def ccno_dsmz_si_id_re1() -> _TestCCNo:
    return _TestCCNo(
        "DSM 112722",
        "DSM",
        1,
        CCNoId(full="112722", core="112722"),
        [],
        DepositStatus.unk,
        _TestStrain(relation=["SI-ID 2", "DSM 112721"]),
    )


@pytest.fixture
def ccno_dsmz_ccno_re1() -> _TestCCNo:
    return _TestCCNo(
        "DSM 112722",
        "DSM",
        1,
        CCNoId(full="112722", core="112722"),
        [],
        DepositStatus.unk,
        _TestStrain(relation=["DSM 112721"]),
    )


@pytest.fixture
def cache_direct_match(
    si_id_1: dict[int, int],
    deposit_ccno_1: dict[tuple[int, str, str, str], StrainDepositId],
) -> MatchCache:
    return MatchCache(
        deposit_ccno=deposit_ccno_1,
        relation_ccno={},
        si_id=si_id_1,
        si_dp_err=set(),
    )


@pytest.fixture
def cache_mis_match() -> MatchCache:
    return MatchCache(
        deposit_ccno={},
        relation_ccno={},
        si_id={},
        si_dp_err=set(),
    )


@pytest.fixture
def cache_err_match(
    si_dp_err_1: set[int],
    si_id_1: dict[int, int],
    deposit_ccno_1: dict[tuple[int, str, str, str], StrainDepositId],
) -> MatchCache:
    return MatchCache(
        deposit_ccno=deposit_ccno_1,
        relation_ccno={},
        si_id=si_id_1,
        si_dp_err=si_dp_err_1,
    )


@pytest.fixture
def cache_strain_match(
    relation_cache_1: dict[tuple[str, str, str, str], dict[int, int]],
    si_id_1: dict[int, int],
) -> MatchCache:
    return MatchCache(
        deposit_ccno={},
        relation_ccno=relation_cache_1,
        si_id=si_id_1,
        si_dp_err=set(),
    )


@pytest.fixture
def acronym_manager() -> AcronymManager:
    return AcronymManager(CURRENT_VER)
