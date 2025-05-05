from typing import ClassVar
from cafi.container.acr_db import AcrDbEntry, AcrCoreReg

from saim.designation.extract_ccno import identify_ccno
from saim.designation.private.radix_tree import AcrRadixTree, search_acr_or_code_ccno
from saim.shared.data_con.brc import BrcContainer
from saim.shared.data_con.designation import ccno_designation_to_dict


class TestSample:
    kn_acr = AcrRadixTree("DSM")
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
    acr_db: ClassVar[dict[int, AcrDbEntry]] = {1: acr_db_instance}
    cc_db_acr: ClassVar[dict[str, set[int]]] = {"DSM": {1}, "DSMZ": {1}}
    cc_db_code: ClassVar[dict[str, set[int]]] = {"DSM": {1}}
    brc_test = BrcContainer(
        cc_db=acr_db,
        f_cc_db={},
        f_cc_db_acr=cc_db_acr,
        f_cc_db_code=cc_db_code,
        kn_acr=kn_acr,
    )

    def test_valid_ccno_des(self) -> None:
        valid_ccnos = [
            "DSM3",
            "DSM 3",
            "DSM 24413",
            "DSM 03",
            "DSM 003",
            "DSM03",
            "DSM030",
            "DSM-003",
            "DSM - 003",
            "DSM : 003",
            "DSM:3",
        ]

        for ccno in valid_ccnos:
            ccno_des_test = identify_ccno(ccno, self.brc_test)
            assert len(ccno_designation_to_dict(ccno_des_test)) == 3

    def test_non_valid_ccno_des(self) -> None:
        only_designations = [
            "DSM T33",
            "DSMZ 123",
            "DSMZ T 123",
            "DSMZ T-123",
            "DSM",
            "DSMZ",
        ]
        for ccno in only_designations:
            ccno_des_test = identify_ccno(ccno, self.brc_test)
            assert len(ccno_designation_to_dict(ccno_des_test)) == 1

    def test_ccno_splitting(self) -> None:
        test = ["DSM 0123", "DSM0123"]
        for ccno in test:
            ccno_des_test = identify_ccno(ccno, self.brc_test)
            assert len(ccno_designation_to_dict(ccno_des_test)) == 3
            assert ccno_des_test.acr == "DSM"
            assert ccno_des_test.id.full == "0123"
            assert ccno_des_test.id.core == "123"
            assert ccno_des_test.designation in test

    def test_search_algo(self) -> None:
        s_kn_acr = AcrRadixTree("DSM")
        s_kn_acr.add("DSMZ")
        assert "DSMZ" == search_acr_or_code_ccno(s_kn_acr, "DSMZ 123").pop()
        assert "DSM" == search_acr_or_code_ccno(s_kn_acr, "DSM 123").pop()
        assert len(search_acr_or_code_ccno(s_kn_acr, "DSMT 123")) == 0
