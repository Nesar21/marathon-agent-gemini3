
import sys
import os
import unittest
from typing import List

# Ensure app is in path
sys.path.insert(0, os.getcwd())

from app.db.schemas import PlanSchema, Component, Resource, Relationship
from app.engine.builder import Builder, BuildError
from app.engine.evaluators import ACTIVE_EVALUATORS

class TestDFRStrict(unittest.TestCase):
    
    def test_strict_domain_rejection(self):
        """Builder should reject unknown component types."""
        plan = PlanSchema(
            schema_version="1.0",
            project_name="Invalid Type Plan",
            components=[
                Component(id="c1", name="Worker", type="worker", path="/")
            ],
            relationships=[]
        )
        builder = Builder()
        with self.assertRaises(BuildError) as cm:
            builder.build(plan)
        self.assertIn("Unknown component type", str(cm.exception))

    def test_structural_unique_endpoint(self):
        """Builder should reject duplicate API endpoints (Method+Path)."""
        plan = PlanSchema(
            schema_version="1.0",
            project_name="Duplicate Route Plan",
            components=[
                Component(id="be", name="Backend", type="backend", path="/be", resources=[
                    Resource(id="api1", type="api_endpoint", name="API 1", properties={"method": "GET", "path": "/users"}),
                    Resource(id="api2", type="api_endpoint", name="API 2", properties={"method": "GET", "path": "/users"})
                ])
            ],
            relationships=[]
        )
        builder = Builder()
        with self.assertRaises(BuildError) as cm:
            builder.build(plan)
        self.assertIn("UNIQUE_ENDPOINT", str(cm.exception))

    def test_ambiguous_call(self):
        """Builder should reject ambiguous calls (Path matches multiple methods, call has no method)."""
        plan = PlanSchema(
            schema_version="1.0",
            project_name="Ambiguous Call Plan",
            components=[
                Component(id="fe", name="Frontend", type="frontend", path="/fe"),
                Component(id="be", name="Backend", type="backend", path="/be", resources=[
                    Resource(id="get_u", type="api_endpoint", name="Get Users", properties={"method": "GET", "path": "/users"}),
                    Resource(id="post_u", type="api_endpoint", name="Post Users", properties={"method": "POST", "path": "/users"})
                ])
            ],
            relationships=[
                Relationship(source="fe", target="be", type="calls", metadata={"path": "/users"}) # No method specified
            ]
        )
        builder = Builder()
        with self.assertRaises(BuildError) as cm:
            builder.build(plan)
        self.assertIn("NO_AMBIGUOUS_ROUTE", str(cm.exception))

    def test_architectural_violations(self):
        """Evaluators should detect architectural issues."""
        plan = PlanSchema(
            schema_version="1.0",
            project_name="Violation Plan",
            components=[
                Component(id="fe", name="Frontend", type="frontend", path="/fe"),
                Component(id="be", name="Backend", type="backend", path="/be", resources=[
                     Resource(id="api_ok", type="api_endpoint", name="OK API", properties={"method": "GET", "path": "/ok", "schema": {}}),
                     Resource(id="api_bad", type="api_endpoint", name="Bad API", properties={"method": "GET", "path": "/bad"}), # Missing Schema
                     Resource(id="api_method", type="api_endpoint", name="Method API", properties={"method": "POST", "path": "/method", "schema": {}}),
                ]),
                Component(id="db", name="DB", type="database", path="/db", resources=[
                    Resource(id="tbl1", type="database_table", name="Users", properties={}), # Missing Migration
                ]),
                # Component(id="mig", name="Mig", type="backend", path="/mig", resources=[
                #     Resource(id="m1", type="migration", name="Init", properties={})
                # ])
            ],
            relationships=[
                # FE_BE_001 Violation: Call non-existent path
                Relationship(source="fe", target="be", type="calls", metadata={"path": "/missing", "method": "GET"}),
                
                # API_METHOD_MATCH_001 Violation: Call with wrong method
                Relationship(source="fe", target="be", type="calls", metadata={"path": "/method", "method": "GET"}), # Target is POST
            ]
        )
        
        builder = Builder()
        graph = builder.build(plan)
        
        violations = []
        for evaluator in ACTIVE_EVALUATORS:
            violations.extend(evaluator.evaluate(graph))
            
        # Debug print
        # for v in violations:
        #     print(f"{v.rule_id}: {v.message}")
            
        rule_ids = [v.rule_id for v in violations]
        
        self.assertIn("FE_BE_001", rule_ids)
        self.assertIn("API_SCHEMA_001", rule_ids)
        self.assertIn("DB_MIG_001", rule_ids)
        self.assertIn("API_METHOD_MATCH_001", rule_ids)

if __name__ == '__main__':
    unittest.main()
