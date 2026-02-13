
from typing import List, Dict, Any, Protocol
from dataclasses import dataclass
import hashlib
from app.engine.graph import SystemGraph
from app.core.canonicalize import canonicalize_json

@dataclass
class Violation:
    rule_id: str
    message: str
    offending_node: str
    metadata: Dict[str, Any] = None

class RuleEvaluator(Protocol):
    rule_id: str
    def evaluate(self, graph: SystemGraph) -> List[Violation]:
        ...

def generate_violation(rule_id: str, message: str, offending_node: str, dedup_data: Dict[str, Any]) -> Violation:
    """
    Helper to generate deterministic violation with hash ID.
    """
    # Deterministic ID generation: sha256(rule_id + offending_node + canonical_details)
    payload = {
        "rule_id": rule_id,
        "offending_node": offending_node,
        **dedup_data
    }
    v_id = hashlib.sha256(canonicalize_json(payload).encode()).hexdigest()
    
    return Violation(
        rule_id=rule_id,
        message=f"{message} (ID: {v_id[:8]})",
        offending_node=offending_node,
        metadata={"violation_hash": v_id, **dedup_data}
    )

class FeBeMatchEvaluator:
    rule_id = "FE_BE_001"
    
    def evaluate(self, graph: SystemGraph) -> List[Violation]:
        violations = []
        edges = graph.edges
        for edge in edges:
            if edge.type == "calls":
                source_node = graph.get_node(edge.source)
                target_node = graph.get_node(edge.target)
                
                # Check if source is Frontend
                is_frontend = False
                if source_node.type == 'component':
                     is_frontend = source_node.properties.get('comp_type') == 'frontend'
                
                if is_frontend:
                    # Frontend API call must exist in backend.
                    # Structural existence is guaranteed by Builder for IDs.
                    # But we must verify the Semantics (Path/Method) match if specified in metadata.
                    
                    call_path = edge.metadata.get('path') if edge.metadata else None
                    if call_path:
                        resolved_node = target_node
                        if target_node.type == 'component':
                            # Re-resolve (Builder logic)
                            children_edges = graph.find_outgoing_edges(target_node.id, 'contains')
                            for e in children_edges:
                                child = graph.get_node(e.target)
                                if child.type == 'api_endpoint':
                                    props = child.properties or {}
                                    if props.get('path') == call_path:
                                        resolved_node = child
                                        break
                        
                        # Now check if resolved node is actually in backend
                        # Find parent component of resolved_node
                        parents = graph.find_incoming_edges(resolved_node.id, 'contains')
                        is_backend_target = False
                        if parents:
                            parent_id = parents[0].source
                            parent = graph.get_node(parent_id)
                            if parent.type == 'component' and parent.properties.get('comp_type') == 'backend':
                                is_backend_target = True
                        
                        if not is_backend_target:
                             violations.append(generate_violation(
                                self.rule_id,
                                f"Frontend calls {call_path} which is not a Backend API.",
                                edge.source,
                                {"target": resolved_node.id, "path": call_path}
                            ))

        return violations

class ApiSchemaEvaluator:
    rule_id = "API_SCHEMA_001"
    
    def evaluate(self, graph: SystemGraph) -> List[Violation]:
        violations = []
        api_nodes = graph.find_nodes_by_type('api_endpoint')
        
        for node in api_nodes:
            props = node.properties or {}
            # Check for generic 'schema' property or specific request/response
            # MVP: "API endpoint must declare schema" -> generic presence check
            has_schema = 'schema' in props or 'request_schema' in props or 'response_schema' in props
            
            if not has_schema:
                violations.append(generate_violation(
                    self.rule_id,
                    f"API Endpoint {node.name} ({props.get('path', 'unknown')}) missing schema declaration.",
                    node.id,
                    {"path": props.get('path')}
                ))
        return violations

class DbMigEvaluator:
    rule_id = "DB_MIG_001"
    
    def evaluate(self, graph: SystemGraph) -> List[Violation]:
        violations = []
        tables = graph.find_nodes_by_type("database_table")
        for table in tables:
            # Check for incoming 'creates' edge from a 'migration' node
            # Allow migration to be resource OR component (builder allows 'migration' resource)
            incoming = graph.find_incoming_edges(table.id, "creates")
            has_migration = False
            for edge in incoming:
                source = graph.get_node(edge.source)
                if source.type == "migration":
                    has_migration = True
                    break
            
            if not has_migration:
                violations.append(generate_violation(
                    self.rule_id,
                    f"Table {table.name} is not created by any migration.",
                    table.id,
                    {"table_name": table.name}
                ))
        return violations

class ApiMethodMatchEvaluator:
    rule_id = "API_METHOD_MATCH_001"
    
    def evaluate(self, graph: SystemGraph) -> List[Violation]:
        violations = []
        edges = graph.edges
        for edge in edges:
            if edge.type == "calls":
                call_method = edge.metadata.get('method') if edge.metadata else None
                if call_method:
                    target_node = graph.get_node(edge.target)
                    
                    # Resolve if targeting component
                    if target_node.type == 'component':
                        call_path = edge.metadata.get('path')
                        children_edges = graph.find_outgoing_edges(target_node.id, 'contains')
                        for e in children_edges:
                            child = graph.get_node(e.target)
                            if child.type == 'api_endpoint' and child.properties.get('path') == call_path:
                                target_node = child
                                break
                    
                    if target_node.type == 'api_endpoint':
                        target_method = target_node.properties.get('method')
                        if target_method and target_method.upper() != call_method.upper():
                             violations.append(generate_violation(
                                self.rule_id,
                                f"HTTP Method Mismatch: Call uses {call_method}, Endpoint expects {target_method}.",
                                edge.source,
                                {"call_method": call_method, "target_method": target_method, "path": edge.metadata.get('path')}
                            ))
        return violations

# Registry of all active evaluators
ACTIVE_EVALUATORS = [
    FeBeMatchEvaluator(),
    ApiSchemaEvaluator(),
    DbMigEvaluator(),
    ApiMethodMatchEvaluator()
]
