from semantic_matcher.model import SemanticMatch, EquivalenceTable


def return_simple_example_equivalence_table() -> EquivalenceTable:
    """
    Returns a simple equivalence table with three semantic matches
    """
    table = EquivalenceTable(matches={})
    table.add_semantic_match(
        SemanticMatch(
            base_semantic_id="s-heppner.com/semanticID/one",
            match_semantic_id="s-heppner.com/semanticID/1",
            score=1.,
            meta_information={"matchSource": "Defined by Sebastian Heppner"}
        )
    )
    table.add_semantic_match(
        SemanticMatch(
            base_semantic_id="s-heppner.com/semanticID/two",
            match_semantic_id="s-heppner.com/semanticID/2",
            score=1.,
            meta_information={"matchSource": "Defined by Sebastian Heppner"}
        )
    )
    table.add_semantic_match(
        SemanticMatch(
            base_semantic_id="s-heppner.com/semanticID/one",
            match_semantic_id="s-heppner.com/semanticID/two",
            score=0.8,
            meta_information={"matchSource": "Defined by Sebastian Heppner"}
        )
    )
    return table


if __name__ == '__main__':
    e = return_simple_example_equivalence_table()
    e.to_file("example_equivalence_table.json")
