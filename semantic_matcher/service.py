from typing import List, Optional

import requests
from fastapi import APIRouter

import model
import service_model


class SemanticMatchingService:
    """
    Todo
    """
    def __init__(self, equivalences: model.EquivalenceTable):
        self.router = APIRouter()
        self.router.add_api_route(
            "/get_match",
            self.get_matches,
            methods=["GET"]
        )
        self.equivalence_table: model.EquivalenceTable = equivalences

    def get_matches(
            self,
            request_body: service_model.MatchRequest
    ) -> service_model.MatchResponse:
        """
        A query to match two SubmodelElements semantically.

        Returns a matching score
        """
        # Try first local matching
        matches: List[model.SemanticMatch] = self.equivalence_table.get_local_matches(
            semantic_id=request_body.semantic_id,
            score_limit=request_body.score_limit
        )
        # If the request asks us to only locally look, we're done already
        if request_body.local_only:
            return service_model.MatchResponse(matches=matches)
        # Now look for remote matches:
        additional_remote_matches: List[model.SemanticMatch] = []
        for match in matches:
            remote_matching_service = self._get_matcher_from_semantic_id(match.match_semantic_id)
            remote_matching_request = service_model.MatchRequest(
                semantic_id=match.match_semantic_id,
                # This is a simple "Ungleichung"
                # Unified score is multiplied: score(A->B) * score(B->C)
                # This score should be larger or equal than the requested score_limit:
                # score(A->B) * score(B->C) >= score_limit
                # score(A->B) is well known, as it is the `match.score`
                # => score(B->C) >= (score_limit/score(A->B))
                score_limit=float(request_body.score_limit/match.score),
                # If we already request a remote score, it does not make sense to choose `local_only`
                local_only=False,
                name=request_body.name,
                definition=request_body.definition
            )
            new_matches_response = requests.get(remote_matching_service, data=remote_matching_request)
            match_response: service_model.MatchResponse = service_model.MatchResponse.model_dump_json(
                new_matches_response.json()
            )
            additional_remote_matches.extend(match_response.matches)
        # Finally, put all matches together and return
        matches.extend(additional_remote_matches)
        return service_model.MatchResponse(matches=matches)

    def _get_matcher_from_semantic_id(self, semantic_id: str) -> str:
        """
        Finds the suiting `SemanticMatchingService` for the given `semantic_id`.

        :returns: The endpoint with which the `SemanticMatchingService` can be accessed
        """
        return "Todo"  # todo
