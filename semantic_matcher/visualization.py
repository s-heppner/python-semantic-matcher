import matplotlib.pyplot as plt  # type: ignore
import networkx as nx
import pyvis.network

from semantic_matcher.algorithm import SemanticMatchGraph


def _to_pyvis_network(g: SemanticMatchGraph) -> pyvis.network.Network:
    network = pyvis.network.Network(notebook=True, directed=True, height="600px", width="100%")

    # Manually add nodes and edges with labels for weights
    for node in g.nodes():
        network.add_node(node, label=node)  # Todo: Do something smart with labels, e.g. source

    for source, target, data in g.edges(data=True):
        # This breaks, if weight is missing, but that is expected behaviour, since we need a semantic similarity score
        weight = data["weight"]
        network.add_edge(source, target, label=str(weight), title=f"Weight: {weight}")

    # Enable physics for animation and gravity effects
    # network.force_atlas_2based()
    network.toggle_physics(True)
    network.show_buttons(filter_=['physics'])
    return network


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
    graph_complex.add_edge("A", "B", weight=0.9)
    graph_complex.add_edge("A", "C", weight=0.8)
    graph_complex.add_edge("B", "D", weight=0.7)
    graph_complex.add_edge("C", "D", weight=0.6)
    graph_complex.add_edge("D", "E", weight=0.5)

    net = _to_pyvis_network(graph_complex)

    net.save_graph("graph.html")
