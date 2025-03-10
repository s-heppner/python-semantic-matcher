from typing import Optional, List, Set

from pydantic import BaseModel
import requests
from fastapi import APIRouter, Response

from semantic_matcher import algorithm


class MatchRequest(BaseModel):
    """
    Request body for the :func:`service.SemanticMatchingService.get_match`

    :ivar semantic_id: The semantic ID that we want to find matches for
    :ivar score_limit: The minimum semantic similarity score to look for. Is considered as larger or equal (>=)
    :ivar local_only: If `True`, only check at the local service and do not request other services
    :ivar already_checked_locations: Optional Set of already checked semantic matching services to avoid looping
    """
    semantic_id: str
    score_limit: float
    local_only: bool = True
    already_checked_locations: Optional[Set[str]] = None


class SemanticMatchingService:
    """
    A Semantic Matching Service

    It offers two operations:

    :func:`~.SemanticMatchingService.post_matches` allows to post
    :class:`model.SemanticMatch`es to the :class:`~.SemanticMatchingService`.

    :func:`~.SemanticMatchingService.get_matches` lets users get the
    :class:`model.SemanticMatch`es of the :class:`~.SemanticMatchingService`
    and the respective remote :class:`~.SemanticMatchingService`s.

    Additionally, the internal function
    :func:`~.SemanticMatchingService._get_matcher_from_semantic_id` lets the
    :class:`~.SemanticMatchingService` find the suiting remote
    :class:`~.SemanticMatchingService`s to a given `semantic_id`.
    """
    def __init__(
            self,
            endpoint: str,
            graph: algorithm.SemanticMatchGraph
    ):
        """
        Initializer of :class:`~.SemanticMatchingService`

        :ivar endpoint: The endpoint on which the service listens
        :ivar equivalences: The :class:`model.EquivalenceTable` of the semantic
            equivalences that this :class:`~.SemanticMatchingService` contains.
        """
        self.router = APIRouter()

        self.router.add_api_route(
            "/all_matches",
            self.get_all_matches,
            methods=["GET"]
        )
        self.router.add_api_route(
            "/get_matches",
            self.get_matches,
            response_model=List[algorithm.SemanticMatch],
            methods=["GET"]
        )
        self.router.add_api_route(
            "/post_matches",
            self.post_matches,
            methods=["POST"]
        )
        self.endpoint: str = endpoint
        self.graph: algorithm.SemanticMatchGraph = graph

    def get_all_matches(self):
        """
        Returns all matches stored in the equivalence table-
        """
        matches = self.graph.get_all_matches()
        return matches

    def get_matches(
            self,
            request_body: MatchRequest
    ) -> List[algorithm.SemanticMatch]:
        """
        A query to match two SubmodelElements semantically.

        Returns a matching score
        """
        # Try first local matching
        matches: List[algorithm.SemanticMatch] = algorithm.find_semantic_matches(
            graph=self.graph,
            semantic_id=request_body.semantic_id,
            min_score=request_body.score_limit
        )
        # If the request asks us to only locally look, we're done already
        if request_body.local_only:
            return matches
        # Now look for remote matches:
        additional_remote_matches: List[algorithm.SemanticMatch] = []
        for match in matches:
            # If the `match_semantic_id` has the same namespace as the `base_semantic_id` there is no sense in looking
            # further, since the semantic_id Resolver would return this Semantic Matching Service.
            if match.base_semantic_id.split("/")[0] == match.match_semantic_id.split("/")[0]:
                continue  # Todo: We definitely need to check for namespace, this just takes "https:"

            # We need to make sure we do not go to the same Semantic Matching Service twice.
            # For that we update the already_checked_locations with the current endpoint:
            already_checked_locations: Set[str] = {self.endpoint}
            if request_body.already_checked_locations:
                already_checked_locations.update(request_body.already_checked_locations)

            remote_matching_service = self._get_matcher_from_semantic_id(match.match_semantic_id)
            # If we could not find the remote_matching_service, or we already checked it, we continue
            if remote_matching_service is None or remote_matching_service in already_checked_locations:
                continue
                # Todo: There is an edge case where this would not find all matches:
                #   Imagine we have a situation, where A -> B -> C -> D, but A and C are on SMS1 and B and C are
                #   on SMS2. This would not find the match C, since we already checked SMS1
                #   I guess this is fine for the moment though.

            # This makes it possible to create the match request:
            remote_matching_request = MatchRequest(
                semantic_id=match.match_semantic_id,
                # This is a simple inequality equation:
                #   Unified score is multiplied: score(A->B) * score(B->C)
                #   This score should be larger or equal than the requested score_limit:
                #   score(A->B) * score(B->C) >= score_limit
                #   score(A->B) is well known, as it is the `match.score`
                #   => score(B->C) >= (score_limit/score(A->B))
                score_limit=float(request_body.score_limit/match.score),
                # If we already request a remote score, it does not make sense to choose `local_only`
                local_only=False,
                already_checked_locations=already_checked_locations
            )
            url = f"{remote_matching_service}/get_matches"
            new_matches_response = requests.get(url, json=remote_matching_request.model_dump_json())
            response_matches = [algorithm.SemanticMatch(**match) for match in new_matches_response.json()]
            additional_remote_matches.extend(response_matches)
        # Finally, put all matches together and return
        matches.extend(additional_remote_matches)
        return matches

    def post_matches(
            self,
            request_body: List[algorithm.SemanticMatch]
    ) -> Response:
        for match in request_body:
            self.graph.add_semantic_match(
                base_semantic_id=match.base_semantic_id,
                match_semantic_id=match.match_semantic_id,
                score=match.score,
            )
        return Response(status_code=200)

    @staticmethod
    def _get_matcher_from_semantic_id(semantic_id: str) -> Optional[str]:
        """
        Finds the suiting `SemanticMatchingService` for the given `semantic_id`.

        :returns: The endpoint with which the `SemanticMatchingService` can be accessed
        """
        request_body = {"semantic_id": semantic_id}
        endpoint = config['RESOLVER']['endpoint']
        port = config['RESOLVER'].getint('port')
        url = f"{endpoint}:{port}/get_semantic_matching_service"
        response = requests.get(url, json=request_body)

        # Check if the response is successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response and construct SMSResponse object
            response_json = response.json()
            response_endpoint = response_json['semantic_matching_service_endpoint']
            return response_endpoint

        return None


if __name__ == '__main__':
    import os
    import configparser
    from fastapi import FastAPI
    import uvicorn

    config = configparser.ConfigParser()
    config.read([
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../config.ini.default")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../config.ini")),
    ])

    # Read in `SemanticMatchGraph`.
    # Note, this construct takes the path in the config.ini relative to the location of the config.ini
    match_graph = algorithm.SemanticMatchGraph.from_file(
        filename=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "..",
            config["SERVICE"]["match_graph_file"]
        ))
    )
    SEMANTIC_MATCHING_SERVICE = SemanticMatchingService(
        endpoint=config["SERVICE"]["endpoint"],
        graph=match_graph,
    )
    with open("../README.md", "r") as file:
        description = file.read()
    APP = FastAPI(
        title="Semantic Matching Service",
        description=description,
        contact={
            "name": "Sebastian Heppner",
            "url": "https://github.com/s-heppner",
        },
    )
    APP.include_router(
        SEMANTIC_MATCHING_SERVICE.router
    )
    uvicorn.run(APP, host=config["SERVICE"]["LISTEN_ADDRESS"], port=int(config["SERVICE"]["PORT"]))
