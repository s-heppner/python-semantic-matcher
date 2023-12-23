from typing import List, Optional

from fastapi import APIRouter

import matcher
import service_model


class SemanticMatchingService:
    """
    Todo
    """
    def __init__(self, semantic_matcher: matcher.SemanticMatcher):
        self.router = APIRouter()
        self.router.add_api_route(
            "/get_match",
            self.get_matches,
            methods=["GET"]
        )
        self.semantic_matcher: matcher.SemanticMatcher = semantic_matcher

    def get_matches(
            self,
            request_body: service_model.MatchRequest
    ) -> service_model.MatchResponse:
        """
        A query to match two SubmodelElements semantically.

        Returns a matching score
        """
        # Try first local matching
        matches: Optional[List[matcher.SemanticMatch]] = self.semantic_matcher.get_matches(request_body.semantic_id)
        if matches is None:
            matches = []
        # If the request asks us to only locally look, we're done already
        if request_body.local_only:
            return service_model.MatchResponse(matches=matches)

        # Todo: There is a difference between searching and matching two given semantic IDs

    def _get_matcher_from_semantic_id(self, semantic_id: str):
        pass
