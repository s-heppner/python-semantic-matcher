import unittest
from typing import List
import os
import json

from semantic_matcher import algorithm


class TestSemanticMatchGraph(unittest.TestCase):
    TEST_FILE = "test_graph.json"

    def setUp(self):
        """Set up a test graph before each test."""
        self.graph = algorithm.SemanticMatchGraph()
        self.graph.add_semantic_match("A", "B", 0.8)
        self.graph.add_semantic_match("B", "C", 0.6)
        self.graph.add_semantic_match("C", "D", 0.9)

    def tearDown(self):
        """Remove the test file after each test."""
        if os.path.exists(self.TEST_FILE):
            os.remove(self.TEST_FILE)

    def test_get_all_matches_basic(self):
        """Test that all direct semantic matches are returned correctly."""
        matches = self.graph.get_all_matches()

        expected_matches = [
            algorithm.SemanticMatch(base_semantic_id="A", match_semantic_id="B", score=0.8, path=[]),
            algorithm.SemanticMatch(base_semantic_id="B", match_semantic_id="C", score=0.6, path=[]),
            algorithm.SemanticMatch(base_semantic_id="C", match_semantic_id="D", score=0.9, path=[]),
        ]

        self.assertEqual(len(matches), 3, "Incorrect number of matches retrieved.")
        self.assertCountEqual(expected_matches, matches, "Matches do not match expected results.")

    def test_get_all_matches_empty_graph(self):
        """Test that an empty graph returns an empty list."""
        empty_graph = algorithm.SemanticMatchGraph()
        matches = empty_graph.get_all_matches()
        self.assertEqual([], matches, "Empty graph should return an empty list.")

    def test_get_all_matches_duplicate_edges(self):
        """Test handling of duplicate edges with different scores."""
        self.graph.add_semantic_match("A", "B", 0.9)  # Overwriting edge
        matches = self.graph.get_all_matches()

        expected_matches = [
            algorithm.SemanticMatch(base_semantic_id="A", match_semantic_id="B", score=0.9, path=[]),
            algorithm.SemanticMatch(base_semantic_id="B", match_semantic_id="C", score=0.6, path=[]),
            algorithm.SemanticMatch(base_semantic_id="C", match_semantic_id="D", score=0.9, path=[]),
        ]

        self.assertEqual(len(matches), 3, "Duplicate edge handling failed.")
        self.assertCountEqual(expected_matches, matches, "Matches do not match expected results.")

    def test_get_all_matches_varying_weights(self):
        """Test that matches with different weights are retrieved correctly."""
        self.graph.add_semantic_match("D", "E", 0.3)
        self.graph.add_semantic_match("E", "F", 1.0)
        matches = self.graph.get_all_matches()

        expected_matches = [
            algorithm.SemanticMatch(base_semantic_id="A", match_semantic_id="B", score=0.8, path=[]),
            algorithm.SemanticMatch(base_semantic_id="B", match_semantic_id="C", score=0.6, path=[]),
            algorithm.SemanticMatch(base_semantic_id="C", match_semantic_id="D", score=0.9, path=[]),
            algorithm.SemanticMatch(base_semantic_id="D", match_semantic_id="E", score=0.3, path=[]),
            algorithm.SemanticMatch(base_semantic_id="E", match_semantic_id="F", score=1.0, path=[]),
        ]

        self.assertEqual(len(matches), 5, "Incorrect number of matches retrieved.")
        self.assertCountEqual(expected_matches, matches, "Matches do not match expected results.")

    def test_to_file(self):
        """Test that the graph is correctly saved to a file."""
        self.graph.to_file(self.TEST_FILE)

        # Check if file exists
        self.assertTrue(os.path.exists(self.TEST_FILE), "File was not created.")

        # Load file content and verify JSON structure
        with open(self.TEST_FILE, "r") as file:
            data = json.load(file)

        self.assertIsInstance(data, list, "File content should be a list of matches.")
        self.assertEqual(len(data), 3, "Incorrect number of matches stored in file.")

        expected_data = [
            {"base_semantic_id": "A", "match_semantic_id": "B", "score": 0.8, "path": []},
            {"base_semantic_id": "B", "match_semantic_id": "C", "score": 0.6, "path": []},
            {"base_semantic_id": "C", "match_semantic_id": "D", "score": 0.9, "path": []},
        ]

        self.assertEqual(data, expected_data, "File content does not match expected data.")

    def test_from_file(self):
        """Test that a graph can be correctly loaded from a file."""
        self.graph.to_file(self.TEST_FILE)
        loaded_graph = algorithm.SemanticMatchGraph.from_file(self.TEST_FILE)

        # Check if the loaded graph has the same edges and weights
        self.assertEqual(len(loaded_graph.edges()), 3, "Loaded graph has incorrect number of edges.")

        for u, v, data in self.graph.edges(data=True):
            self.assertTrue(loaded_graph.has_edge(u, v), f"Edge {u} -> {v} is missing in loaded graph.")
            self.assertEqual(loaded_graph[u][v]["weight"], data["weight"], f"Edge weight mismatch for {u} -> {v}")

    def test_empty_graph(self):
        """Test saving and loading an empty graph."""
        empty_graph = algorithm.SemanticMatchGraph()
        empty_graph.to_file(self.TEST_FILE)
        loaded_graph = algorithm.SemanticMatchGraph.from_file(self.TEST_FILE)

        self.assertEqual(len(loaded_graph.edges()), 0, "Loaded graph should be empty.")


class TestSemanticMatch(unittest.TestCase):
    def test_str_representation(self):
        """Test that __str__ correctly formats the path and score."""
        match = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )

        expected_str = "A -> B = 0.8"
        self.assertEqual(expected_str, str(match), "__str__ method output is incorrect")

    def test_str_representation_longer_path(self):
        """Test __str__ output with a longer path."""
        match = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="D",
            score=0.6,
            path=["A", "B", "C"]
        )

        expected_str = "A -> B -> C -> D = 0.6"
        self.assertEqual(expected_str, str(match), "__str__ method output is incorrect for longer paths")

    def test_str_representation_no_path(self):
        """Test __str__ output when there's no path (direct match)."""
        match = algorithm.SemanticMatch(
            base_semantic_id="X",
            match_semantic_id="Y",
            score=1.0,
            path=[]
        )

        expected_str = "Y = 1.0"  # No path, just the match
        self.assertEqual(expected_str, str(match), "__str__ method output is incorrect for empty path")

    def test_hash_consistency(self):
        """Test that identical SemanticMatch instances have the same hash."""
        match1 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )
        match2 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )

        self.assertEqual(hash(match1), hash(match2), "Hashes of identical objects should be the same")

    def test_hash_uniqueness(self):
        """Test that different SemanticMatch instances have different hashes."""
        match1 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )
        match2 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="C",
            score=0.8,
            path=["A"]
        )

        self.assertNotEqual(hash(match1), hash(match2), "Hashes of different objects should be different")

    def test_hash_set_usage(self):
        """Test that SemanticMatch instances can be used in a set (ensuring uniqueness)."""
        match1 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )
        match2 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )
        match3 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="C",
            score=0.9,
            path=["A"]
        )

        match_set = {match1, match2, match3}
        self.assertEqual(len(match_set), 2, "Set should contain unique elements based on hash")

    def test_hash_dict_usage(self):
        """Test that SemanticMatch instances can be used as dictionary keys."""
        match1 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )
        match2 = algorithm.SemanticMatch(
            base_semantic_id="A",
            match_semantic_id="B",
            score=0.8,
            path=["A"]
        )

        match_dict = {match1: "First Entry", match2: "Second Entry"}

        self.assertEqual(len(match_dict), 1, "Identical objects should overwrite each other in a dictionary")
        self.assertEqual(match_dict[match1], "Second Entry", "Latest value should be stored in dictionary")


class TestFindSemanticMatches(unittest.TestCase):
    def setUp(self):
        """Set up test graphs for various cases."""
        self.graph = algorithm.SemanticMatchGraph()

        # Populate the graph
        self.graph.add_edge("A", "B", weight=0.8)
        self.graph.add_edge("B", "C", weight=0.7)
        self.graph.add_edge("C", "D", weight=0.9)
        self.graph.add_edge("B", "D", weight=0.6)
        self.graph.add_edge("D", "E", weight=0.5)

    def test_basic_functionality(self):
        """Test basic propagation of semantic matches."""
        matches: List[algorithm.SemanticMatch] = algorithm.find_semantic_matches(self.graph, "A", min_score=0)
        str_matches: List[str] = [str(i) for i in matches]
        expected = [
            f"A -> B = 0.8",
            f"A -> B -> C = {0.8*0.7}",  # 0.56
            f"A -> B -> C -> D = {0.8*0.7*0.9}",  # 0.504
            f"A -> B -> D = {0.8*0.6}",  # 0.48
            f"A -> B -> C -> D -> E = {0.8 * 0.7 * 0.9 * 0.5}",  # 0.252
            f"A -> B -> D -> E = {0.8 * 0.6 * 0.5}",  # 0.24
        ]
        self.assertEqual(expected, str_matches)

    def test_loop_prevention(self):
        """Ensure that loops do not cause infinite recursion."""
        self.graph.add_edge("D", "A", weight=0.4)  # Creates a loop

        matches: List[algorithm.SemanticMatch] = algorithm.find_semantic_matches(
            self.graph,
            semantic_id="A",
            min_score=0.1
        )

        # We would expect the algorithm to have only traversed the graph exactly once!
        self.assertEqual(6, len(matches))
        # For simplifying the analysis, we remove everything but the `semantic_id`s of the found matches
        matched_semantic_ids: List[str] = [i.match_semantic_id for i in matches]
        self.assertIn("D", matched_semantic_ids)
        self.assertNotIn("A", matched_semantic_ids)  # "A" should not be revisited

    def test_minimum_threshold(self):
        """Ensure that results below the minimum score are excluded."""
        matches = algorithm.find_semantic_matches(self.graph, "A", min_score=0.6)
        str_matches: List[str] = [str(i) for i in matches]
        expected: List[str] = [
            "A -> B = 0.8"
        ]
        self.assertEqual(expected, str_matches)

    def test_not_in_graph(self):
        """Test that matches that are not in the graph are not found"""
        matches = algorithm.find_semantic_matches(self.graph, semantic_id="X", min_score=0)
        self.assertEqual(0, len(matches))

    def test_disconnected_graph(self):
        """Test behavior when the graph has disconnected components."""
        graph_disconnected = algorithm.SemanticMatchGraph()
        graph_disconnected.add_edge("A", "B", weight=0.8)
        graph_disconnected.add_edge("X", "Y", weight=0.9)

        matches = algorithm.find_semantic_matches(graph_disconnected, "A", min_score=0.1)
        str_matches: List[str] = [str(i) for i in matches]
        expected: List[str] = [
            "A -> B = 0.8"
        ]

        self.assertEqual(expected, str_matches)

    def test_empty_graph(self):
        """Test behavior when the graph is empty."""
        graph_empty = algorithm.SemanticMatchGraph()
        matches = algorithm.find_semantic_matches(graph_empty, "A", min_score=0.1)

        self.assertEqual(0, len(matches))

    def test_single_node_no_edges(self):
        """Test behavior when the graph has only one node and no edges."""
        graph_single = algorithm.SemanticMatchGraph()
        graph_single.add_node("A")

        matches = algorithm.find_semantic_matches(graph_single, "A", min_score=0.1)

        self.assertEqual(0, len(matches))

    def test_edge_case_weights(self):
        """Test behavior with edge weights close to zero and one."""
        graph_edge_cases = algorithm.SemanticMatchGraph()
        graph_edge_cases.add_edge("A", "B", weight=1.0, source="perfect match")
        graph_edge_cases.add_edge("B", "C", weight=0.01, source="weak match")

        matches = algorithm.find_semantic_matches(graph_edge_cases, "A", min_score=0.01)
        matches_str: List[str] = [str(i) for i in matches]
        expected: List[str] = [
            f"A -> B = {1.0}",
            f"A -> B -> C = {1.0*0.01}",
        ]
        self.assertEqual(expected, matches_str)

    def test_complex_graph(self):
        """Test behavior in a complex graph with multiple branches."""
        graph_complex = algorithm.SemanticMatchGraph()
        graph_complex.add_edge("A", "B", weight=0.9, source="dataset1")
        graph_complex.add_edge("A", "C", weight=0.8, source="dataset2")
        graph_complex.add_edge("B", "D", weight=0.7, source="dataset3")
        graph_complex.add_edge("C", "D", weight=0.6, source="dataset4")
        graph_complex.add_edge("D", "E", weight=0.5, source="dataset5")

        matches = algorithm.find_semantic_matches(graph_complex, "A", min_score=0.3)
        matches_str: List[str] = [str(i) for i in matches]
        expected: List[str] = [
            f"A -> B = {0.9}",  # 0.9
            f"A -> C = {0.8}",  # 0.8
            f"A -> B -> D = {0.9*0.7}",  # 0.63
            f"A -> C -> D = {0.8*0.6}",  # 0.48
            f"A -> B -> D -> E = {0.9*0.7*0.5}",  # 0.315
            # f"A -> B -> C -> E = {0.8*0.6*0.5}",  # 0.24 => out
        ]
        self.assertEqual(expected, matches_str)


if __name__ == "__main__":
    unittest.main()
