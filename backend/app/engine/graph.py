
import networkx as nx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class NodeData:
    id: str
    type: str # 'component', 'api', 'table', etc.
    name: str
    properties: Dict[str, Any] = None

@dataclass
class EdgeData:
    source: str
    target: str
    type: str
    metadata: Dict[str, Any] = None

class SystemGraph:
    """
    Defensive wrapper around NetworkX DiGraph.
    Represents the architecture as a directed graph of Components, Files, and Resources.
    """
    def __init__(self):
        self._graph = nx.MultiDiGraph()
        self._frozen = False

    def add_node(self, id: str, type: str, name: str, **kwargs):
        if self._frozen:
            raise RuntimeError("Graph is frozen")
        self._graph.add_node(id, type=type, name=name, **kwargs)

    def add_edge(self, source: str, target: str, type: str, **kwargs):
        if self._frozen:
            raise RuntimeError("Graph is frozen")
        if not self._graph.has_node(source):
            raise ValueError(f"Source node {source} does not exist")
        if not self._graph.has_node(target):
            raise ValueError(f"Target node {target} does not exist")
        
        self._graph.add_edge(source, target, type=type, **kwargs)

    def freeze(self):
        self._frozen = True
        # NetworkX freeze is actually nx.freeze(G), which makes it immutable
        nx.freeze(self._graph)

    # --- Accessors ---

    @property
    def nodes(self) -> List[NodeData]:
        return [
            NodeData(id=n, **self._graph.nodes[n]) 
            for n in self._graph.nodes
        ]

    @property
    def edges(self) -> List[EdgeData]:
        return [
            EdgeData(source=u, target=v, **data)
            for u, v, data in self._graph.edges(data=True)
        ]

    def get_node(self, node_id: str) -> Optional[NodeData]:
        if not self._graph.has_node(node_id):
            return None
        return NodeData(id=node_id, **self._graph.nodes[node_id])

    def find_nodes_by_type(self, type: str) -> List[NodeData]:
        # Filter nodes by type attribute
        nodes = []
        for n, data in self._graph.nodes(data=True):
            if data.get('type') == type:
                nodes.append(NodeData(id=n, **data))
        return nodes

    def find_incoming_edges(self, node_id: str, edge_type: Optional[str] = None) -> List[EdgeData]:
        edges = []
        if self._graph.has_node(node_id):
            for u, v, data in self._graph.in_edges(node_id, data=True):
                if edge_type is None or data.get('type') == edge_type:
                    edges.append(EdgeData(source=u, target=v, **data))
        return edges

    def find_outgoing_edges(self, node_id: str, edge_type: Optional[str] = None) -> List[EdgeData]:
        edges = []
        if self._graph.has_node(node_id):
            for u, v, data in self._graph.out_edges(node_id, data=True):
                if edge_type is None or data.get('type') == edge_type:
                    edges.append(EdgeData(source=u, target=v, **data))
        return edges

    def find_matching_endpoints(self, path_pattern: str, method: str = None) -> List[NodeData]:
        """
        Find API nodes that match a specific path pattern (and optional method).
        This is a simplified matcher.
        """
        # API nodes usually have properties={'path': ..., 'method': ...}
        api_nodes = self.find_nodes_by_type('api')
        matches = []
        for node in api_nodes:
            props = node.properties or {}
            node_path = props.get('path')
            node_method = props.get('method')
            
            # Use simple string matching for MVP
            if node_path == path_pattern:
                if method:
                    if node_method and node_method.upper() == method.upper():
                        matches.append(node)
                else:
                    matches.append(node)
        return matches
