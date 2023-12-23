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
    meta_information: Dict


class EquivalenceTable(BaseModel):
    matches: Dict[str, List[SemanticMatch]]

    def add_semantic_match(self, match: SemanticMatch) -> None:
        if self.matches.get(match.base_semantic_id) is not None:
            self.equivalence_table[match.base_semantic_id].append(match)
        else:
            self.equivalence_table[match.base_semantic_id] = [match]

    def remove_semantic_match(self, match: SemanticMatch) -> None:
        if self.equivalence_table.get(match.base_semantic_id) is not None:
            self.equivalence_table.get(match.base_semantic_id).remove(match)
            if len(self.equivalence_table.get(match.base_semantic_id)) == 0:
                self.equivalence_table.pop(match.base_semantic_id)

    def to_file(self, filename: str) -> None:
        with open(filename, "w") as file:
            file.write(self.model_dump_json(indent=4))

    @classmethod
    def from_file(cls, filename: str) -> "EquivalenceTable":
        with open(filename, "r") as file:
            return EquivalenceTable.model_validate_json(file.read())
