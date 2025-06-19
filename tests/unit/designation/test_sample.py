from typing import Never

from saim.designation.extract_ccno import (
    extract_ccno_from_text,
    identify_all_valid_ccno,
    identify_ccno,
)
from saim.designation.known_acr_db import create_brc_con
from saim.shared.data_con.brc import BrcContainer
from saim.shared.data_con.designation import CCNoDes, CCNoId, ccno_designation_to_dict
from saim.shared.search.radix_tree import RadixTree, find_first_match_with_fix, radix_add


pytest_plugins = ("tests.fixture.designation",)


class TestSample:

    def test_valid_ccno_des(self, brc_simple: BrcContainer) -> None:
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
            ccno_des_test = identify_ccno(ccno, brc_simple)
            assert len(ccno_designation_to_dict(ccno_des_test)) == 3

    def test_non_valid_ccno_des(self, brc_simple: BrcContainer) -> None:
        only_designations = [
            "DSM T33",
            "DSMZ 123",
            "DSMZ T 123",
            "DSMZ T-123",
            "DSM",
            "DSMZ",
        ]
        for ccno in only_designations:
            ccno_des_test = identify_ccno(ccno, brc_simple)
            assert len(ccno_designation_to_dict(ccno_des_test)) == 1

    def test_ccno_splitting(self, brc_simple: BrcContainer) -> None:
        test = ["DSM 0123", "DSM0123"]
        for ccno in test:
            ccno_des_test = identify_ccno(ccno, brc_simple)
            assert len(ccno_designation_to_dict(ccno_des_test)) == 3
            assert ccno_des_test.acr == "DSM"
            assert ccno_des_test.id.full == "0123"
            assert ccno_des_test.id.core == "123"
            assert ccno_des_test.designation in test

    def test_search_algo(self) -> None:
        s_kn_acr: RadixTree[Never] = RadixTree("DSM", tuple())
        radix_add(s_kn_acr, "DSMZ", tuple())
        assert "DSMZ" == find_first_match_with_fix(s_kn_acr, "DSMZ 123").pop()[0]
        assert "DSM" == find_first_match_with_fix(s_kn_acr, "DSM 123").pop()[0]
        assert len(find_first_match_with_fix(s_kn_acr, "DSMT 123")) == 0

    def test_search_ccno_all(self, brc_ambiguous: BrcContainer) -> None:
        res = identify_all_valid_ccno("DSM-T 1234", brc_ambiguous)
        assert len(res) == 2
        res = identify_all_valid_ccno("DSM T-1234.1", brc_ambiguous)
        assert len(res) == 1
        assert res[0].acr == "DSM T"

    def test_search_ccno_all_text(self, brc_ambiguous: BrcContainer) -> None:
        test_text = """
Described in literature was DSM-T 1234 strain and DSM T-1234.2.
        """
        test_res = list(extract_ccno_from_text(test_text, brc_ambiguous))
        assert len(test_res) == 3
        for ccno in (
            CCNoDes(
                acr="DSM",
                id=CCNoId(pre="T", full="T 1234", core="1234"),
                designation="DSM-T 1234",
            ),
            CCNoDes(
                acr="DSM-T",
                id=CCNoId(full="1234", core="1234"),
                designation="DSM-T 1234",
            ),
            CCNoDes(
                acr="DSM T",
                id=CCNoId(full="1234.2", core="1234.2"),
                designation="DSM T-1234.2",
            ),
        ):
            assert ccno in test_res

    def test_search_algo_text(self) -> None:
        brc_full_test = create_brc_con()
        test_text = """
The laboratory conducted several tests to identify microbial strains.
Among the samples tested were DSM:123 and AtcC BAA12 andATCC BAA13.
These strains showed unique resistance patterns against common antibiotics.
Additional testing involved DSM T12 for its distinctive properties.
Researchers noted peculiar growth rates when exposed to varying temperatures.
Subsequent studies focused on strain IMI12*i, known for rapid mutation capabilities.
Data from these tests were compiled into comprehensive reports for further analysis.
Cross-comparison with historical data provided insights into evolutionary trends.
Further experiments are planned to explore potential applications in biotechnology.
Collaboration with international labs aims to enhance the understanding of genetics.
        """
        test_res = list(extract_ccno_from_text(test_text, brc_full_test))
        assert len(test_res) == 3
        for ccno in [
            CCNoDes(acr="DSM", id=CCNoId(full="123", core="123"), designation="DSM 123"),
            CCNoDes(
                acr="ATCC",
                id=CCNoId(full="BAA12", core="12", pre="BAA"),
                designation="ATCC BAA 12",
            ),
            CCNoDes(
                acr="IMI",
                id=CCNoId(full="12*i", core="12", suf="i"),
                designation="IMI12i",
            ),
        ]:
            assert ccno not in test_res
        for ccno in [
            CCNoDes(acr="DSM", id=CCNoId(full="123", core="123"), designation="DSM:123"),
            CCNoDes(
                acr="ATCC",
                id=CCNoId(full="BAA12", core="12", pre="BAA"),
                designation="AtcC BAA12",
            ),
            CCNoDes(
                acr="IMI",
                id=CCNoId(full="12*i", core="12", suf="*i"),
                designation="IMI12*i",
            ),
        ]:
            assert ccno in test_res
