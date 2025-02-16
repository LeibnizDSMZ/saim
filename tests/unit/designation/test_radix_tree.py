from saim.designation.private.radix_tree import AcrRadixTree


class TestRadixTree:
    @staticmethod
    def _check_node_keys(
        tree_node: AcrRadixTree | None, keys: list[str], next_key: str, /
    ) -> AcrRadixTree | None:
        assert tree_node is not None
        assert tree_node.keys == keys
        last_node = len(keys) == 0
        assert tree_node.end is last_node
        if last_node:
            return None
        return tree_node.get_next(next_key)

    def test_create_node(self) -> None:
        tree = AcrRadixTree("DSMZ")
        assert isinstance(tree, AcrRadixTree)

    def test_create_node_and_compact(self) -> None:
        tree = AcrRadixTree("DSMZ")
        tree.compact()
        assert tree.keys == ["DSMZ"]

    def test_create_multiple_nodes(self) -> None:
        tree = AcrRadixTree("DSMZ")
        tree.add("KCTC")
        tree.add("JCC")
        tree.add("TCC")
        tree.add("DSM")
        assert tree.keys == ["D", "K", "J", "T"]

    def test_create_multiple_nodes_and_compact(self) -> None:
        tree = AcrRadixTree("DSMZ")
        tree.add("DSM")
        tree.add("TCC")
        tree.add("JCC")
        tree.add("JXX")
        tree.add("KCKC")
        tree.add("KCTC")

        tree.compact()
        assert tree.keys == ["J", "DSM", "TCC", "KC"]

    def test_end(self) -> None:
        test_string = "ABC"
        tree_node: AcrRadixTree | None = AcrRadixTree(test_string)
        for key_v in test_string:
            assert tree_node is not None
            tree_node = TestRadixTree._check_node_keys(tree_node, [key_v], key_v)
