import os
import configparser
import multiprocessing

import requests
import unittest

from fastapi import FastAPI
import uvicorn

from semantic_matcher import model
from semantic_matcher.model import SemanticMatch
from semantic_matcher.service import SemanticMatchingService

from contextlib import contextmanager
import signal
import time

import json as js


def run_server():
    # Load test configuration
    config = configparser.ConfigParser()
    config.read([
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../test_resources/config.ini")),
    ])

    # Read in equivalence table
    EQUIVALENCES = model.EquivalenceTable.from_file(
        filename=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "..",
            config["SERVICE"]["equivalence_table_file"]
        ))
    )

    # Initialise SemanticMatchingService
    semantic_matching_service = SemanticMatchingService(
        endpoint=config["SERVICE"]["endpoint"],
        equivalences=EQUIVALENCES
    )

    # Mock resolver
    def mock_get_matcher(self, semantic_id):
        return "http://remote-service:8000"

    SemanticMatchingService._get_matcher_from_semantic_id = mock_get_matcher

    # Mock remote service
    original_requests_get = requests.get

    class SimpleResponse:
        def __init__(self, content: str, status_code: int = 200):
            self.text = content
            self.status_code = status_code

    def mock_requests_get(url, json):
        if url == "http://remote-service:8000/get_matches":
            match_one = SemanticMatch(
                base_semantic_id="s-heppner.com/semanticID/three",
                match_semantic_id="remote-service.com/semanticID/tres",
                score=1.0,
                meta_information={"matchSource": "Defined by Moritz Sommer",
                                  "path": ["remote-service.com/semanticID/trois"]}
            )
            matches_data = {
                "matches": [match_one.model_dump()]
            }
            matches_json = js.dumps(matches_data)
            return SimpleResponse(content=matches_json)
        else:
            return original_requests_get(url, json=json)

    requests.get = mock_requests_get

    # Run server
    app = FastAPI()
    app.include_router(semantic_matching_service.router)
    uvicorn.run(app, host=config["SERVICE"]["ENDPOINT"], port=int(config["SERVICE"]["PORT"]), log_level="error")


@contextmanager
def run_server_context():
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    try:
        time.sleep(2)  # Wait for the server to start
        yield
    finally:
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            os.kill(server_process.pid, signal.SIGKILL)
            server_process.join()


class TestSemanticMatchingService(unittest.TestCase):

    def test_get_all_matches(self):
        with run_server_context():
            response = requests.get("http://localhost:8000/all_matches")
            expected_matches = {
                's-heppner.com/semanticID/one': [
                    {
                        'base_semantic_id': 's-heppner.com/semanticID/one',
                        'match_semantic_id': 's-heppner.com/semanticID/1',
                        'score': 1.0,
                        'meta_information': {'matchSource': 'Defined by Sebastian Heppner'}
                    },
                    {
                        'base_semantic_id': 's-heppner.com/semanticID/one',
                        'match_semantic_id': 's-heppner.com/semanticID/two',
                        'score': 0.8,
                        'meta_information': {'matchSource': 'Defined by Sebastian Heppner'}
                    }
                ],
                's-heppner.com/semanticID/two': [
                    {
                        'base_semantic_id': 's-heppner.com/semanticID/two',
                        'match_semantic_id': 's-heppner.com/semanticID/2',
                        'score': 1.0,
                        'meta_information': {'matchSource': 'Defined by Sebastian Heppner'}
                    }
                ],
                's-heppner.com/semanticID/three': [
                    {
                        'base_semantic_id': 's-heppner.com/semanticID/three',
                        'match_semantic_id': 'remote-service.com/semanticID/trois',
                        'score': 1.0,
                        'meta_information': {'matchSource': 'Defined by Moritz Sommer'}
                    }
                ]
            }
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_post_matches(self):
        with run_server_context():
            new_match = {
                "base_semantic_id": "s-heppner.com/semanticID/new",
                "match_semantic_id": "s-heppner.com/semanticID/3",
                "score": 0.95,
                "meta_information": {"matchSource": "Defined by UnitTest"}
            }
            matches_list = {
                "matches": [new_match]
            }
            requests.post(
                "http://localhost:8000/post_matches",
                json=matches_list
            )
            response = requests.get("http://localhost:8000/all_matches")
            actual_matches = response.json()
            self.assertIn("s-heppner.com/semanticID/new", actual_matches)
            self.assertEqual(
                actual_matches["s-heppner.com/semanticID/new"][0]["match_semantic_id"],
                "s-heppner.com/semanticID/3"
            )

            self.assertEqual(
                actual_matches["s-heppner.com/semanticID/new"][0]["score"],
                0.95
            )

            self.assertEqual(
                actual_matches["s-heppner.com/semanticID/new"][0]["meta_information"]["matchSource"],
                "Defined by UnitTest"
            )

    def test_get_matches_local_only(self):
        with run_server_context():
            match_request = {
                "semantic_id": "s-heppner.com/semanticID/one",
                "score_limit": 0.5,
                "local_only": True
            }
            response = requests.get("http://localhost:8000/get_matches", json=match_request)
            expected_matches = {
                "matches": [
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/one",
                        "match_semantic_id": "s-heppner.com/semanticID/1",
                        "score": 1.0,
                        "meta_information": {"matchSource": "Defined by Sebastian Heppner"}
                    },
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/one",
                        "match_semantic_id": "s-heppner.com/semanticID/two",
                        "score": 0.8,
                        "meta_information": {"matchSource": "Defined by Sebastian Heppner"}
                    },
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/one",
                        "match_semantic_id": "s-heppner.com/semanticID/2",
                        "score": 0.8,
                        "meta_information": {"matchSource": "Defined by Sebastian Heppner",
                                             "path": ["s-heppner.com/semanticID/two"]}
                    }
                ]
            }
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_get_matches_local_and_remote(self):
        with run_server_context():
            match_request = {
                "semantic_id": "s-heppner.com/semanticID/three",
                "score_limit": 0.7,
                "local_only": False
            }
            response = requests.get("http://localhost:8000/get_matches", json=match_request)
            expected_matches = {
                "matches": [
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/three",
                        "match_semantic_id": "remote-service.com/semanticID/trois",
                        "score": 1.0,
                        "meta_information": {"matchSource": "Defined by Moritz Sommer"}
                    },
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/three",
                        "match_semantic_id": "remote-service.com/semanticID/tres",
                        "score": 1.0,
                        "meta_information": {"matchSource": "Defined by Moritz Sommer",
                                             "path": ["remote-service.com/semanticID/trois"]}
                    },
                ]
            }
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_get_matches_no_matches(self):
        with run_server_context():
            match_request = {
                "semantic_id": "s-heppner.com/semanticID/unknown",
                "score_limit": 0.5,
                "local_only": True
            }
            response = requests.get("http://localhost:8000/get_matches", json=match_request)
            expected_matches = {"matches": []}
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_get_matches_with_low_score_limit(self):
        with run_server_context():
            match_request = {
                "semantic_id": "s-heppner.com/semanticID/one",
                "score_limit": 0.9,
                "local_only": True
            }
            response = requests.get("http://localhost:8000/get_matches", json=match_request)
            expected_matches = {
                "matches": [
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/one",
                        "match_semantic_id": "s-heppner.com/semanticID/1",
                        "score": 1.0,
                        "meta_information": {"matchSource": "Defined by Sebastian Heppner"}
                    }
                ]
            }
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_get_matches_with_nlp_parameters(self):
        with run_server_context():
            match_request = {
                "semantic_id": "s-heppner.com/semanticID/one",
                "score_limit": 0.5,
                "local_only": True,
                "name": "Example Name",
                "definition": "Example Definition"
            }
            response = requests.get("http://localhost:8000/get_matches", json=match_request)
            expected_matches = {
                "matches": [
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/one",
                        "match_semantic_id": "s-heppner.com/semanticID/1",
                        "score": 1.0,
                        "meta_information": {"matchSource": "Defined by Sebastian Heppner"}
                    },
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/one",
                        "match_semantic_id": "s-heppner.com/semanticID/two",
                        "score": 0.8,
                        "meta_information": {"matchSource": "Defined by Sebastian Heppner"}
                    },
                    {
                        "base_semantic_id": "s-heppner.com/semanticID/one",
                        "match_semantic_id": "s-heppner.com/semanticID/2",
                        "score": 0.8,
                        "meta_information": {"matchSource": "Defined by Sebastian Heppner",
                                             "path": ["s-heppner.com/semanticID/two"]}
                    }
                ]
            }
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_remove_all_matches(self):
        with run_server_context():
            requests.post("http://localhost:8000/clear")
            response = requests.get("http://localhost:8000/all_matches")
            expected_matches = {}
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)


if __name__ == '__main__':
    unittest.main()
