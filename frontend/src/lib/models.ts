
// DTOs matching backend Pydantic models

export interface Resource {
    id: string;
    type: string; // 'api', 'table', 'migration', 'topic', 'job'
    name: string;
    description?: string;
    properties: Record<string, any>;
}

export interface Component {
    id: string;
    name: string;
    type: 'frontend' | 'backend' | 'database' | 'worker' | 'cli';
    path: string;
    resources: Resource[];
    dependencies: string[]; // Component IDs
}

export interface Relationship {
    source: string;
    target: string;
    type: 'calls' | 'creates' | 'reads' | 'updates' | 'deletes' | 'depends_on';
    metadata?: Record<string, any>;
}

export interface PlanSchema {
    schema_version: string;
    project_name: string;
    components: Component[];
    relationships: Relationship[];
    env_vars?: Record<string, string>;
}

export interface Violation {
    rule_id: string;
    message: string;
    offending_node: string;
    metadata?: Record<string, any>;
}

export interface DFR {
    plan_hash: string;
    engine_version: string;
    passed: boolean;
    violations: Violation[];
    timestamp: string; // ISO date
}

export interface PlanPatch {
    operation: 'add' | 'remove' | 'modify';
    path: string;
    value: any;
}

export interface AISuggestion {
    violation_id: string;
    suggestion: string;
    confidence: 'high' | 'medium' | 'low';
    patches: PlanPatch[];
}

export interface User {
    id: string;
    email: string;
    plan_tier: string;
    created_at: string;
}

export interface APIKey {
    id: string;
    provider: string;
    model_id: string;
    is_active: boolean;
    created_at: string;
}

export interface Token {
    access_token: string;
    token_type: string;
}
