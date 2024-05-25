from typing import Dict, List

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
            self.matches[match.base_semantic_id].append(match)
        else:
            self.matches[match.base_semantic_id] = [match]

    def remove_semantic_match(self, match: SemanticMatch) -> None:
        if self.matches.get(match.base_semantic_id) is not None:
            self.matches.get(match.base_semantic_id).remove(match)
            if len(self.matches.get(match.base_semantic_id)) == 0:
                self.matches.pop(match.base_semantic_id)

    def get_local_matches(self, semantic_id: str, score_limit: float) -> List[SemanticMatch]:
        equivalence_table_result = self.matches.get(semantic_id)
        if equivalence_table_result is None:
            return []
        for match in equivalence_table_result:
            matching_result = []
            if match.score > score_limit:
                matching_result.append(match)
        return matching_result

    def get_all_matches(self) -> List[SemanticMatch]:
        return self.matches

    def to_file(self, filename: str) -> None:
        with open(filename, "w") as file:
            file.write(self.model_dump_json(indent=4))

    @classmethod
    def from_file(cls, filename: str) -> "EquivalenceTable":
        with open(filename, "r") as file:
            return EquivalenceTable.model_validate_json(file.read())

