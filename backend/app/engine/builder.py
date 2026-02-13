
from typing import List, Dict, Any, Set
from app.db.schemas import PlanSchema
from app.engine.graph import SystemGraph

# Strict Domain Boundary
ALLOWED_COMPONENT_TYPES = {'frontend', 'backend', 'database'}
ALLOWED_RESOURCE_TYPES = {'api_endpoint', 'database_table', 'migration'}
ALLOWED_EDGE_TYPES = {'calls', 'creates', 'reads', 'updates', 'deletes', 'depends_on'}

class BuildError(Exception):
    """Raised when plan contains ambiguous or invalid relationships"""
    pass

class Builder:
    def build(self, plan: PlanSchema) -> SystemGraph:
        """
        Constructs a SystemGraph from a PlanSchema.
        Rejects ambiguous architectures and enforces strict domain.
        """
        graph = SystemGraph()
        
        # 1. Add Components and Resources as Nodes
        for comp in plan.components:
            # Domain Boundary Check: Component Type
            if comp.type not in ALLOWED_COMPONENT_TYPES:
                raise BuildError(f"Unknown component type: '{comp.type}'. Allowed: {ALLOWED_COMPONENT_TYPES}")
                
            graph.add_node(
                id=comp.id,
                type='component', 
                name=comp.name,
                properties={"path": comp.path, "comp_type": comp.type}
            )
            
            for res in comp.resources:
                # Domain Boundary Check: Resource Type
                # Map 'api' -> 'api_endpoint' for user friendliness if needed? 
                # User provided 'api_endpoint' and 'database_table'.
                # Let's support both 'api' (common) and 'api_endpoint' (strict) by normalizing?
                # No, user said "Input (Plan) -> Normalize". 
                # We assume plan input uses 'api' or 'table' from our schema, 
                # OR we force schema to use 'api_endpoint'.
                # Current schema allows 'str'. Let's strictly enforce 'api_endpoint' and 'database_table'.
                # But existing samples use 'api', 'table'. 
                # COMPATIBILITY: I will map 'api'->'api_endpoint', 'table'->'database_table' internally
                # BUT reject anything else.
                
                res_type = res.type
                if res_type == 'api': res_type = 'api_endpoint'
                if res_type == 'table': res_type = 'database_table'
                
                if res_type not in ALLOWED_RESOURCE_TYPES:
                     raise BuildError(f"Unknown resource type: '{res.type}'. Allowed: {ALLOWED_RESOURCE_TYPES}")

                graph.add_node(
                    id=res.id,
                    type=res_type,
                    name=res.name,
                    properties=res.properties
                )
                
                # Link Component -> Resource (contains)
                graph.add_edge(comp.id, res.id, type='contains')

        # 2. Add Relationships as Edges
        for rel in plan.relationships:
            # Domain Boundary Check: Edge Type
            # 'api_call' mapping needed? 
            # Plan uses 'calls', 'creates' etc.
            if rel.type not in ALLOWED_EDGE_TYPES:
                 raise BuildError(f"Unknown relationship type: '{rel.type}'. Allowed: {ALLOWED_EDGE_TYPES}")

            # Structural Rule: COMPONENT_EXISTS / DEPENDENCY_EXISTS
            # Handled by graph.add_edge raising ValueError if node missing
            try:
                graph.add_edge(
                    source=rel.source, 
                    target=rel.target, 
                    type=rel.type,
                    metadata=rel.metadata
                )
            except ValueError as e:
                # Map to Structural Rule Failure
                raise BuildError(f"Structural Violation (DEPENDENCY_EXISTS): {e}")

        # 3. Reject Ambiguity (Core Requirement)
        self._reject_ambiguity(graph)

        # 4. Freeze
        graph.freeze()
        return graph

    def _reject_ambiguity(self, graph: SystemGraph) -> None:
        """
        Fail build if any relationship is ambiguous.
        Rules:
        1. UNIQUE_ENDPOINT: Duplicate API routes
        2. NO_AMBIGUOUS_ROUTE: Frontend calls resolving to >1 endpoints
        """
        
        # 1. UNIQUE_ENDPOINT
        api_nodes = graph.find_nodes_by_type('api_endpoint')
        routes = {} # (method, path) -> list of node_ids
        
        for node in api_nodes:
            props = node.properties or {}
            method = props.get('method', '').upper()
            path = props.get('path', '')
            
            if method and path:
                key = (method, path)
                if key in routes:
                    raise BuildError(
                        f"Structural Violation (UNIQUE_ENDPOINT): {method} {path} declared in multiple resources: "
                        f"{routes[key]} and {node.id}"
                    )
                routes[key] = node.id

        # 2. NO_AMBIGUOUS_ROUTE (Resolution Check)
        edges = graph.edges
        for edge in edges:
            if edge.type == 'calls':
                # Check for explicit 'path' metadata leading to ambiguity
                target_node = graph.get_node(edge.target)
                call_path = edge.metadata.get('path') if edge.metadata else None
                call_method = edge.metadata.get('method') if edge.metadata else None
                
                if call_path and target_node.type == 'component':
                     # Resolve call to component -> child resource
                    children_edges = graph.find_outgoing_edges(target_node.id, 'contains')
                    children_ids = [e.target for e in children_edges]
                    
                    found = []
                    for child_id in children_ids:
                        child = graph.get_node(child_id)
                        if child.type == 'api_endpoint':
                            props = child.properties or {}
                            if props.get('path') == call_path:
                                if call_method:
                                    # Strict Method Match if provided
                                    if props.get('method', '').upper() == call_method.upper():
                                        found.append(child)
                                else:
                                    # Relaxed match (any method) - debatable for "Deterministic"
                                    # But if method not specified in call, maybe any match is valid?
                                    # User Constraints: "Input (Plan) -> Normalize". 
                                    # Let's assume input always has method if it's an API call.
                                    pass
                                    found.append(child)
                    
                    if len(found) > 1:
                         raise BuildError(f"Structural Violation (NO_AMBIGUOUS_ROUTE): Call to {call_path} on {target_node.name} is ambiguous. Matches: {[n.id for n in found]}")


