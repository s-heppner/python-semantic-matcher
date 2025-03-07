import matplotlib.pyplot as plt  # type: ignore
import networkx as nx

from semantic_matcher.algorithm import SemanticMatchGraph

# Todo: This is WIP


def save_graph_as_figure(g: SemanticMatchGraph, filename: str) -> None:
    """
    A simple visualization of a `SemanticMatchGraph` saved as picture
    """
    # Draw the graph
    plt.figure()
    pos = nx.spring_layout(g)  # Positions for nodes
    nx.draw(g, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=3000, font_size=10)

    # Add edge labels
    edge_labels = {(u, v): f"{d['weight']:.2f}" for u, v, d in g.edges(data=True)}
    nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels)

    plt.savefig(filename)


if __name__ == "__main__":
    graph_complex = SemanticMatchGraph()
    graph_complex.add_edge("A", "B", weight=0.9, source="dataset1")
    graph_complex.add_edge("A", "C", weight=0.8, source="dataset2")
    graph_complex.add_edge("B", "D", weight=0.7, source="dataset3")
    graph_complex.add_edge("C", "D", weight=0.6, source="dataset4")
    graph_complex.add_edge("D", "E", weight=0.5, source="dataset5")

    save_graph_as_figure(graph_complex, "temp.png")
