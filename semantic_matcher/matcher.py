from typing import Optional, Dict, List

from pydantic import BaseModel


class SemanticMatch(BaseModel):
    """
    A semantic match, mapping two semanticIDs with a matching score. Can be imagined as a weighted graph with
    `base_semantic_id` ---`score`---> `match_semantic_id`

    Todo: Think about static and TTL, but that is optimization
    Todo: Maybe we want to have the matching method as debug information
    """
    base_semantic_id: str
    match_semantic_id: str
    score: float


class SemanticMatcher:
    def __init__(
            self,
            equivalence_table: Optional[Dict[str, List[SemanticMatch]]] = None
    ):
        if equivalence_table is None:
            equivalence_table = {}
        self.equivalence_table: Dict[str, List[SemanticMatch]] = equivalence_table

    def add_semantic_match(
            self,
            base_semantic_id: str,
            match_semantic_id: str,
            score: float,
    ) -> None:
        semantic_match: SemanticMatch = SemanticMatch(
            base_semantic_id=base_semantic_id,
            match_semantic_id=match_semantic_id,
            score=score,
        )
        if self.equivalence_table.get(base_semantic_id) is not None:
            self.equivalence_table[base_semantic_id].append(semantic_match)
        else:
            self.equivalence_table[base_semantic_id] = [semantic_match]

    def remove_semantic_match(
            self,
            semantic_match: SemanticMatch
    ) -> None:
        if self.equivalence_table.get(semantic_match.base_semantic_id) is not None:
            self.equivalence_table.get(semantic_match.base_semantic_id).remove(semantic_match)
            if len(self.equivalence_table.get(semantic_match.base_semantic_id)) == 0:
                self.equivalence_table.pop(semantic_match.base_semantic_id)

    def get_matches(self, semantic_id: str) -> Optional[List[SemanticMatch]]:
        return self.equivalence_table.get(semantic_id)
