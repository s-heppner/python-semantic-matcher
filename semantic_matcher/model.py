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
            if match not in self.matches[match.base_semantic_id]:
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
        matching_result = []
        for match in equivalence_table_result:
            if match.score > score_limit:
                matching_result.append(match)
                rec_result = self.get_local_matches(match.match_semantic_id, score_limit/match.score)
                for rec_match in rec_result:
                    rec_match.base_semantic_id = match.base_semantic_id
                    rec_match.score *= match.score
                    if "path" not in rec_match.meta_information:
                        rec_match.meta_information["path"] = []
                    rec_match.meta_information["path"].insert(0, match.match_semantic_id)
                if rec_result is not None:
                    matching_result += rec_result
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

