from saim.shared.search.radix_tree import RadixTree, radix_add
from saim.taxon_name.extract_taxa import extract_taxa_from_text


def test_extract_taxa_from_text() -> None:
    lar = "Eubacterium limosum"
    radix = RadixTree(lar, (1,))
    radix_add(radix, "Eubacterium", (2,))
    radix_add(radix, "Campylobacter coli", (3,))
    res = set(
        extract_taxa_from_text(
            "Find Campylobacter-coli as Eubacterium limosum", radix, len(lar)
        )
    )
    assert res == {1, 2, 3}
