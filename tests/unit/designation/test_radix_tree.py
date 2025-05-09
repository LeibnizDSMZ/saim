from typing import Never
from saim.shared.search.radix_tree import (
    RadixTree,
    radix_add,
    radix_compact,
    radix_get_next,
    radix_keys,
)


class TestRadixTree:
    @staticmethod
    def _check_node_keys(
        tree_node: RadixTree[Never] | None, keys: list[str], next_key: str, /
    ) -> RadixTree[Never] | None:
        assert tree_node is not None
        assert radix_keys(tree_node) == keys
        last_node = len(keys) == 0
        assert tree_node.end is last_node
        if last_node:
            return None
        return radix_get_next(tree_node, next_key)

    def test_create_node(self) -> None:
        tree: RadixTree[Never] = RadixTree("DSMZ", tuple())
        assert isinstance(tree, RadixTree)

    def test_create_node_and_compact(self) -> None:
        tree: RadixTree[Never] = RadixTree("DSMZ", tuple())
        radix_compact(tree)
        assert radix_keys(tree) == ["DSMZ"]

    def test_create_multiple_nodes(self) -> None:
        tree: RadixTree[Never] = RadixTree("DSMZ", tuple())
        radix_add(tree, "KCTC", tuple())
        radix_add(tree, "JCC", tuple())
        radix_add(tree, "TCC", tuple())
        radix_add(tree, "DSM", tuple())
        assert radix_keys(tree) == ["D", "K", "J", "T"]

    def test_create_multiple_nodes_and_compact(self) -> None:
        tree: RadixTree[Never] = RadixTree("DSMZ", tuple())
        radix_add(tree, "DSM", tuple())
        radix_add(tree, "TCC", tuple())
        radix_add(tree, "JCC", tuple())
        radix_add(tree, "JXX", tuple())
        radix_add(tree, "KCKC", tuple())
        radix_add(tree, "KCTC", tuple())
        radix_compact(tree)
        assert radix_keys(tree) == ["J", "DSM", "TCC", "KC"]

    def test_end(self) -> None:
        test_string = "ABC"
        tree_node: RadixTree[Never] | None = RadixTree(test_string, tuple())
        for key_v in test_string:
            assert tree_node is not None
            tree_node = TestRadixTree._check_node_keys(tree_node, [key_v], key_v)
