from typing import List

import requests
from fastapi import APIRouter

from semantic_matcher import model, service_model


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
            equivalences: model.EquivalenceTable
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
            methods=["GET"]
        )
        self.router.add_api_route(
            "/post_matches",
            self.post_matches,
            methods=["POST"]
        )
        self.router.add_api_route(
            "/clear",
            self.remove_all_matches,
            methods=["POST"]
        )
        self.endpoint: str = endpoint
        self.equivalence_table: model.EquivalenceTable = equivalences

    def get_all_matches(self):
        """
        Returns all matches stored in the equivalence table-
        """
        matches = self.equivalence_table.get_all_matches()
        return matches

    def remove_all_matches(self):
        self.equivalence_table.remove_all_semantic_matches()

    def get_matches(
            self,
            request_body: service_model.MatchRequest
    ) -> service_model.MatchesList:
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
            return service_model.MatchesList(matches=matches)
        # Now look for remote matches:
        additional_remote_matches: List[model.SemanticMatch] = []
        for match in matches:
            if match.base_semantic_id.split("/")[0] == match.match_semantic_id.split("/")[0]:
                #match_id is local
                continue
            remote_matching_service = self._get_matcher_from_semantic_id(match.match_semantic_id)
            if remote_matching_service is None:
                continue
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
            url = f"{remote_matching_service}/get_matches"
            new_matches_response = requests.get(url, json=remote_matching_request.dict())
            match_response = service_model.MatchesList.model_validate_json(new_matches_response.text)
            additional_remote_matches.extend(match_response.matches)
        # Finally, put all matches together and return
        matches.extend(additional_remote_matches)
        res = service_model.MatchesList(matches=matches)
        return res

    def post_matches(
            self,
            request_body: service_model.MatchesList
    ) -> None:
        for match in request_body.matches:
            self.equivalence_table.add_semantic_match(match)
        # Todo: Figure out how to properly return 200

    def _get_matcher_from_semantic_id(self, semantic_id: str) -> str:
        """
        Finds the suiting `SemanticMatchingService` for the given `semantic_id`.

        :returns: The endpoint with which the `SemanticMatchingService` can be accessed
        """
        request_body = {"semantic_id": semantic_id}
        endpoint = config['RESOLVER']['endpoint']
        port = config['RESOLVER'].getint('port')
        url = f"{endpoint}:{port}/get_semantic_matching_service"
        response = requests.get(url, json=request_body.dict())

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

    # Read in equivalence table
    # Note, this construct takes the path in the config.ini relative to the
    # location of the config.ini
    EQUIVALENCES = model.EquivalenceTable.from_file(
        filename=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "..",
            config["SERVICE"]["equivalence_table_file"]
        ))
    )
    SEMANTIC_MATCHING_SERVICE = SemanticMatchingService(
        endpoint=config["SERVICE"]["endpoint"],
        equivalences=EQUIVALENCES
    )
    APP = FastAPI()
    APP.include_router(
        SEMANTIC_MATCHING_SERVICE.router
    )
    uvicorn.run(APP, host="0.0.0.0", port=int(config["SERVICE"]["PORT"]))
