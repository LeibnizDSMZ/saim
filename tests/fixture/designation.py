from typing import Never
import pytest
from cafi.container.acr_db import AcrDbEntry, AcrCoreReg
from saim.shared.search.radix_tree import RadixTree, radix_add
from saim.shared.data_con.brc import BrcContainer


@pytest.fixture
def brc_simple() -> BrcContainer:
    kn_acr: RadixTree[Never] = RadixTree("DSM", tuple())
    kn_rev: RadixTree[Never] = RadixTree("MSD", tuple())
    acr_db_instance = AcrDbEntry(
        acr="DSM",
        code="DSMZ",
        name="DSMZ-German Collection of Microorganisms and Cell Cultures GmbH",
        country="DE",
        active=True,
        regex_ccno="^DSM\\s*\\d+$",
        regex_id=AcrCoreReg(full="^\\d+$", core="\\d+"),
        deprecated=False,
        homepage="https://www.dsmz.de/",
        catalogue=["https://www.dsmz.de/collection/catalogue/details/culture/<acr>-<id>"],
        acr_changed_to=[],
        acr_synonym=["DSMZ"],
    )
    acr_db = {1: acr_db_instance}
    cc_db_acr = {"DSM": {1}, "DSMZ": {1}}
    cc_db_code = {"DSMZ": {1}}
    return BrcContainer(
        cc_db=acr_db,
        f_cc_db={},
        f_cc_db_acr=cc_db_acr,
        f_cc_db_code=cc_db_code,
        kn_acr=kn_acr,
        kn_acr_rev=kn_rev,
    )


@pytest.fixture
def brc_ambiguous() -> BrcContainer:
    acr_db_inst_pre = AcrDbEntry(
        acr="DSM",
        code="DSMZ",
        name="DSMZ-German Collection of Microorganisms and Cell Cultures GmbH",
        country="DE",
        active=True,
        regex_ccno="^DSM\\s*T\\s*\\d+$",
        regex_id=AcrCoreReg(pre="T", full="^T\\s*\\d+$", core="\\d+"),
        deprecated=False,
        homepage="https://www.dsmz.de/",
        catalogue=["https://www.dsmz.de/collection/catalogue/details/culture/<acr>-<id>"],
        acr_changed_to=[],
        acr_synonym=["DSMZ"],
    )
    acr_db_inst_pre_inlcuded = AcrDbEntry(
        acr="DSM:T",
        code="DSMZ:T",
        name="DSMZ-German Collection of Microorganisms and Cell Cultures GmbH",
        country="DE",
        active=True,
        regex_ccno="^DSM-T\\s*\\d+$",
        regex_id=AcrCoreReg(full="^\\d+(\\.\\d+)?$", core="\\d+(\\.\\d+)?"),
        deprecated=False,
        homepage="https://www.dsmz.de/",
        catalogue=["https://www.dsmz.de/collection/catalogue/details/culture/<acr>-<id>"],
        acr_changed_to=[],
        acr_synonym=["DSMZ"],
    )
    acr_db_amb: dict[int, AcrDbEntry] = {1: acr_db_inst_pre, 2: acr_db_inst_pre_inlcuded}

    kn_acr: RadixTree[Never] = RadixTree("DSM", tuple())
    kn_rev: RadixTree[Never] = RadixTree("MSD", tuple())
    radix_add(kn_acr, "DSM:T", tuple())
    radix_add(kn_rev, "T:MSD", tuple())
    cc_db_acr_amb: dict[str, set[int]] = {
        "DSM": {1},
        "DSMT": {2},
    }
    cc_db_code_amb: dict[str, set[int]] = {"DSMZ": {1, 2}}
    return BrcContainer(
        cc_db=acr_db_amb,
        f_cc_db={},
        f_cc_db_acr=cc_db_acr_amb,
        f_cc_db_code=cc_db_code_amb,
        kn_acr=kn_acr,
        kn_acr_rev=kn_rev,
    )
