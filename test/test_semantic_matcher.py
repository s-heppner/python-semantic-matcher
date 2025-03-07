import os
import multiprocessing

import requests
import unittest

from fastapi import FastAPI
import uvicorn

from semantic_matcher import algorithm
from semantic_matcher.service import SemanticMatchingService

from contextlib import contextmanager
import signal
import time

import json as js


def run_server():
    # Read in equivalence table
    match_graph = algorithm.SemanticMatchGraph.from_file(
        filename=os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "test_resources/example_graph.json"
        ))
    )

    # Initialise SemanticMatchingService
    semantic_matching_service = SemanticMatchingService(
        endpoint="localhost",
        graph=match_graph
    )

    # Mock semantic_id Resolver
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
            match_one = algorithm.SemanticMatch(
                base_semantic_id="s-heppner.com/semanticID/three",
                match_semantic_id="remote-service.com/semanticID/tres",
                score=1.0,
                path=[]
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
    uvicorn.run(app, host="localhost", port=8000, log_level="error")


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
            expected_matches = [
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/one',
                 'match_semantic_id': 'https://s-heppner.com/semantic_id/uno',
                 'path': [],
                 'score': 0.9},
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/one',
                 'match_semantic_id': 'https://remote.com/semantic_id/deux',
                 'path': [],
                 'score': 0.7},
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/uno',
                 'match_semantic_id': 'https://s-heppner.com/semantic_id/trois',
                 'path': [],
                 'score': 0.6}
            ]
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_post_matches(self):
        with run_server_context():
            new_match = {
                "base_semantic_id": "https://s-heppner.com/semantic_id/new",
                "match_semantic_id": "https://s-heppner.com/semantic_id/nouveaux",
                "score": 0.95,
                "path": [],
            }
            response = requests.post(
                "http://localhost:8000/post_matches",
                json=[new_match]
            )
            self.assertEqual(200, response.status_code)
            # Todo: Make sure this does not become a problem in other tests

    def test_get_matches_local_only(self):
        with run_server_context():
            match_request = {
                "semantic_id": "https://s-heppner.com/semantic_id/one",
                "score_limit": 0.5,
                "local_only": True
            }
            response = requests.get("http://localhost:8000/get_matches", json=match_request)
            expected_matches = [
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/one',
                 'match_semantic_id': 'https://s-heppner.com/semantic_id/uno',
                 'path': ['https://s-heppner.com/semantic_id/one'],
                 'score': 0.9},
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/one',
                 'match_semantic_id': 'https://remote.com/semantic_id/deux',
                 'path': ['https://s-heppner.com/semantic_id/one'],
                 'score': 0.7},
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/one',
                 'match_semantic_id': 'https://s-heppner.com/semantic_id/trois',
                 'path': ['https://s-heppner.com/semantic_id/one',
                          'https://s-heppner.com/semantic_id/uno'],
                 'score': 0.54}
            ]
            actual_matches = response.json()
            self.assertEqual(expected_matches, actual_matches)

    def test_get_matches_local_and_remote(self):
        with run_server_context():
            match_request = {
                "semantic_id": "https://s-heppner.com/semantic_id/one",
                "score_limit": 0.7,
                "local_only": False
            }
            response = requests.get("http://localhost:8000/get_matches", json=match_request)
            expected_matches = [
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/one',
                 'match_semantic_id': 'https://s-heppner.com/semantic_id/uno',
                 'path': ['https://s-heppner.com/semantic_id/one'],
                 'score': 0.9},
                {'base_semantic_id': 'https://s-heppner.com/semantic_id/one',
                 'match_semantic_id': 'https://remote.com/semantic_id/deux',
                 'path': ['https://s-heppner.com/semantic_id/one'],
                 'score': 0.7}
            ]
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
            actual_matches = response.json()
            self.assertEqual([], actual_matches)


if __name__ == '__main__':
    unittest.main()
