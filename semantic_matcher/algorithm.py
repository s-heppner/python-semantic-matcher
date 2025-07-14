import json
from typing import List, Tuple
import heapq

import networkx as nx
from pydantic import BaseModel
from neo4j import GraphDatabase


class SemanticMatchGraph(nx.DiGraph):
    def __init__(self):
        super().__init__()

    def add_semantic_match(self,
                           base_semantic_id: str,
                           match_semantic_id: str,
                           score: float):
        self.add_edge(
            u_of_edge=base_semantic_id,
            v_of_edge=match_semantic_id,
            weight=score,
        )

    def get_all_matches(self) -> List["SemanticMatch"]:
        matches: List["SemanticMatch"] = []

        # Iterate over all edges in the graph
        for base, match, data in self.edges(data=True):
            score = data.get("weight", 0.0)  # Get weight, default to 0.0 if missing
            matches.append(SemanticMatch(
                base_semantic_id=base,
                match_semantic_id=match,
                score=score,
                path=[]  # Direct match, no intermediate nodes
            ))

        return matches

    def to_file(self, filename: str):
        with open(filename, "w") as file:
            matches = [match.model_dump() for match in self.get_all_matches()]
            json.dump(matches, file, indent=4)

    @classmethod
    def from_file(cls, filename: str) -> "SemanticMatchGraph":
        with open(filename, "r") as file:
            matches_data = json.load(file)
        graph = SemanticMatchGraph()
        for match_data in matches_data:
            graph.add_semantic_match(
                base_semantic_id=match_data["base_semantic_id"],
                match_semantic_id=match_data["match_semantic_id"],
                score=match_data["score"]
            )
        return graph

    def to_neo4j(self, url: str, user: str, password: str):
        driver = GraphDatabase.driver(url, auth=(user, password))
        with driver.session() as session:
            # Optional: clear previous graph
            session.run("MATCH (n) DETACH DELETE n")

            for u, v, data in self.edges(data=True):
                session.run("""
                    MERGE (a:Semantic {id: $u})
                    MERGE (b:Semantic {id: $v})
                    MERGE (a)-[:MATCH {score: $score}]->(b)
                """, u=u, v=v, score=data["weight"])
        driver.close()

    @classmethod
    def from_neo4j(cls, url: str, user: str, password: str) -> "SemanticMatchGraph":
        graph = cls()
        driver = GraphDatabase.driver(url, auth=(user, password))
        with driver.session() as session:
            result = session.run("""
                MATCH (a:Semantic)-[r:MATCH]->(b:Semantic)
                RETURN a.id AS u, b.id AS v, r.score AS score
            """)
            for record in result:
                graph.add_semantic_match(record["u"], record["v"], record["score"])
        driver.close()
        return graph


class SemanticMatch(BaseModel):
    base_semantic_id: str
    match_semantic_id: str
    score: float
    path: List[str]  # The path of `semantic_id`s that the algorithm took

    def __str__(self) -> str:
        return f"{' -> '.join(self.path + [self.match_semantic_id])} = {self.score}"

    def __hash__(self):
        return hash((
            self.base_semantic_id,
            self.match_semantic_id,
            self.score,
            tuple(self.path),
        ))


def find_semantic_matches(
    graph: SemanticMatchGraph,
    semantic_id: str,
    min_score: float = 0.5
) -> List[SemanticMatch]:
    """
    Find semantic matches for a given node with a minimum score threshold.

    Args:
        graph (nx.DiGraph): The directed graph with weighted edges.
        semantic_id (str): The starting semantic_id.
        min_score (float): The minimum similarity score to consider.
            This value is necessary to ensure the search terminates also with sufficiently large graphs.

    Returns:
        List[SemanticMatch]:
        A list of MatchResults, sorted by their score with the highest score first.
    """
    if semantic_id not in graph:
        return []

    # We need to make sure that all possible paths starting from the given semantic_id are explored.
    # To achieve this, we use the concept of "priority queue". While we could use a simple FIFO list of matches to
    # explore, this way we actually end up with an already sorted result with the highest match at the beginning of the
    # list. As possible implementation of this abstract data structure, we choose to use a "max-heap".
    # However, there is no efficient implementation of a max-heap in Python, so rather we use the built-in "min-heap"
    # and negate the score values. A priority queue ensures that elements with the highest priority are processed first,
    # regardless of when they were added.
    # We initialize the priority queue:
    pq: List[Tuple[float, str, List[str]]] = [(-1.0, semantic_id, [])]  # (neg_score, node, path)
    # The queue is structured as follows:
    #   - `neg_score`: The negative score of the match
    #   - `node`: The `match_semantic_id` of the match
    #   - `path`: The path between the `semantic_id` and the `match_semantic_id`

    # Prepare the result list
    results: List[SemanticMatch] = []

    # Run the priority queue until all possible paths have been explored
    # This means in each iteration:
    #   - We pop the top element of the queue as it's the next highest semantic match we want to explore
    #   - If the match has a score higher or equal to the given `min_score`, we add it to the results
    #   - We add all connected `semantic_id`s to the priority queue to be treated next
    #   - We go to the next element of the queue
    while pq:
        # Get the highest-score match from the queue
        neg_score, node, path = heapq.heappop(pq)
        score = -neg_score  # Convert back to positive

        # Store result if above threshold (except the start node)
        if node != semantic_id and score >= min_score:
            results.append(SemanticMatch(
                base_semantic_id=semantic_id,
                match_semantic_id=node,
                score=score,
                path=path
            ))

        # Traverse to the neighboring and therefore connected `semantic_id`s
        for neighbor, edge_data in graph[node].items():
            edge_weight = edge_data["weight"]
            assert isinstance(edge_weight, float)
            new_score: float = score * edge_weight  # Multiplicative propagation

            # Prevent loops by ensuring we do not revisit the start node after the first iteration
            if neighbor == semantic_id:
                continue  # Avoid re-exploring the start node

            # We add the newly found `semantic_id`s to the queue to be explored next in order of their score
            if new_score >= min_score:
                heapq.heappush(pq, (-new_score, neighbor, path + [node]))  # Push updated path

    return results


if __name__ == '__main__':
    graph_complex = SemanticMatchGraph()
    graph_complex.add_edge("A", "B", weight=0.9)
    graph_complex.add_edge("A", "C", weight=0.8)
    graph_complex.add_edge("B", "D", weight=0.7)
    graph_complex.add_edge("C", "D", weight=0.6)
    graph_complex.add_edge("D", "E", weight=0.5)
    graph_complex.to_neo4j(
        url="bolt://localhost:7687",
        user="neo4j",
        password="your_password"
    )
