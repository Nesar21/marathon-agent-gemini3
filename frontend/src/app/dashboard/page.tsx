
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const SESSION_KEY_NAME = 'gemini_api_key';

interface DFR {
    plan_hash: string;
    engine_version: string;
    passed: boolean;
    violations: any[];
    cache_hit?: boolean;
}

interface AISuggestion {
    violation_id: string;
    suggestion: string;
    confidence: 'high' | 'medium' | 'low';
    patches: any[];
}

interface DashboardStats {
    totalValidations: number;
    passed: number;
    failed: number;
    recentValidations: Array<{ id: string; plan_hash: string; status: string; time: string }>;
    ruleFrequency: Array<{ rule: string; count: number }>;
}

const ENGINE_RULES = [
    { id: 'FE_BE_001', name: 'Frontend→Backend Match', desc: 'Every frontend API call must have a matching backend endpoint' },
    { id: 'API_SCHEMA_001', name: 'API Schema Required', desc: 'Every API endpoint must declare a request/response schema' },
    { id: 'DB_MIG_001', name: 'Migration Coverage', desc: 'Every database table must have a corresponding migration' },
    { id: 'API_METHOD_MATCH_001', name: 'HTTP Method Match', desc: 'Calling method (GET/POST) must match the endpoint declaration' },
];

export default function DashboardPage() {
    const [planJson, setPlanJson] = useState('');
    const [loading, setLoading] = useState(false);
    const [dfr, setDfr] = useState<DFR | null>(null);
    const [error, setError] = useState('');
    const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [disclaimerOpen, setDisclaimerOpen] = useState(false);
    const [modelUsed, setModelUsed] = useState<string>('');

    // Stats
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loadingStats, setLoadingStats] = useState(true);

    useEffect(() => {
        loadStats();
    }, []);

    const loadStats = async () => {
        try {
            const data = await api.getStats();
            setStats(data);
        } catch (e) {
            console.error("Failed to load stats", e);
        } finally {
            setLoadingStats(false);
        }
    };

    const handleValidate = async () => {
        setLoading(true);
        setError('');
        setDfr(null);
        setSuggestions([]);

        try {
            const plan = JSON.parse(planJson);

            // Smart Import: Detect if user pasted a DFR instead of a Plan
            if (plan.plan_hash && Array.isArray(plan.violations) && 'passed' in plan) {
                setTimeout(() => {
                    setDfr(plan as DFR);
                    setLoading(false);
                }, 400);
                return;
            }

            const result = await api.validate(plan);
            setDfr(result);
            loadStats();
        } catch (err: any) {
            if (err instanceof SyntaxError) {
                setError('Invalid JSON — check your syntax');
            } else if (err.response?.status === 413) {
                setError('Payload Too Large — reduce plan size');
            } else {
                const detail = err.response?.data?.detail;
                if (typeof detail === 'object') {
                    setError(`${detail.type || 'Error'}: ${detail.message || JSON.stringify(detail)}`);
                } else {
                    setError(detail || err.message || 'Validation failed');
                }
            }
        } finally {
            if (!planJson.includes('plan_hash')) {
                setLoading(false);
            }
        }
    };

    const handleGetSuggestions = async () => {
        if (!dfr) return;

        const geminiKey = sessionStorage.getItem(SESSION_KEY_NAME);
        if (!geminiKey) {
            setError('No API key found. Go to Settings → AI Provider to add your Gemini key.');
            return;
        }

        setLoadingSuggestions(true);
        setError('');

        try {
            const { data, model, fallback } = await api.getSuggestionsWithMeta({
                plan_hash: dfr.plan_hash,
                engine_version: dfr.engine_version,
                dfr_json: dfr,
                prompt_mode: 'builtin'
            }, geminiKey);
            setSuggestions(data);
            setModelUsed(model || 'Gemini 3 Pro');
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            if (typeof detail === 'object') {
                setError(`${detail.type || 'Error'}: ${detail.message || JSON.stringify(detail)}`);
            } else {
                setError(detail || err.message || 'Failed to get suggestions');
            }
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const SAMPLE_PLANS = {
        valid: {
            schema_version: "1.0",
            project_name: "Canonical Valid Plan",
            components: [
                { id: "frontend", name: "Web Frontend", type: "frontend", path: "/src/web", resources: [], dependencies: ["backend"] },
                {
                    id: "backend", name: "API Server", type: "backend", path: "/src/api",
                    resources: [{ id: "api_users", type: "api", name: "Users API", properties: { method: "GET", path: "/api/users", schema: { response: "UserList" } } }],
                    dependencies: []
                }
            ],
            relationships: [
                { source: "frontend", target: "backend", type: "calls", metadata: { method: "GET", path: "/api/users" } }
            ],
            env_vars: {}
        },
        violation: {
            schema_version: "1.0",
            project_name: "Single Violation Plan",
            components: [
                {
                    id: "database", name: "Primary Database", type: "database", path: "/db",
                    resources: [{ id: "users_table", type: "table", name: "Users", properties: {} }],
                    dependencies: []
                }
            ],
            relationships: [],
            env_vars: {}
        },
        complex: {
            schema_version: "1.0",
            project_name: "Multi-Failure Plan",
            components: [
                { id: "fe", name: "Web App", type: "frontend", path: "/web", resources: [], dependencies: ["be"] },
                { id: "be", name: "API Service", type: "backend", path: "/api", resources: [], dependencies: [] },
                { id: "db", name: "PostgreSQL", type: "database", path: "/db", resources: [{ id: "t1", type: "table", name: "T1" }], dependencies: [] }
            ],
            relationships: [
                { source: "fe", target: "be", type: "calls", metadata: { method: "POST", path: "/missing" } }
            ],
            env_vars: {}
        }
    };

    return (
        <div>
            {/* Page Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1>Dashboard</h1>
                    <p className="text-muted" style={{ marginTop: '0.25rem' }}>Validate system architectures against governance rules</p>
                </div>
            </div>

            {/* ── Engine Disclaimer Banner ── */}
            <div className="disclaimer-banner mb-6">
                <div
                    className="disclaimer-header"
                    onClick={() => setDisclaimerOpen(!disclaimerOpen)}
                >
                    <div className="flex items-center gap-3">
                        <span style={{ fontSize: '1.125rem' }}>⚡</span>
                        <div>
                            <span style={{ fontWeight: 600, color: 'rgb(var(--primary-rgb))', fontSize: '0.875rem' }}>
                                MVP Engine — 4 Architectural Rules
                            </span>
                            <span className="text-muted" style={{ marginLeft: '0.75rem' }}>
                                {disclaimerOpen ? 'Click to collapse' : 'Click to see what this engine checks'}
                            </span>
                        </div>
                    </div>
                    <span style={{ color: 'var(--text-muted)', transition: 'transform 0.2s', transform: disclaimerOpen ? 'rotate(180deg)' : 'rotate(0)' }}>
                        ▼
                    </span>
                </div>

                {disclaimerOpen && (
                    <div className="disclaimer-body">
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                            {ENGINE_RULES.map(rule => (
                                <div key={rule.id} style={{
                                    padding: '0.75rem 1rem',
                                    background: 'rgba(0, 0, 0, 0.2)',
                                    borderRadius: 'var(--radius-sm)',
                                    border: '1px solid var(--border-subtle)'
                                }}>
                                    <code style={{ fontSize: '0.6875rem', color: 'rgb(var(--primary-rgb))' }}>{rule.id}</code>
                                    <div style={{ fontSize: '0.8125rem', fontWeight: 600, marginTop: '0.25rem' }}>{rule.name}</div>
                                    <div className="text-muted" style={{ fontSize: '0.75rem', marginTop: '0.125rem' }}>{rule.desc}</div>
                                </div>
                            ))}
                        </div>
                        <div className="alert alert-warning" style={{ fontSize: '0.8125rem' }}>
                            <strong>Limitations:</strong> Input must be hand-authored JSON plan schemas. No auto-discovery from code.
                            AI suggestions require a Gemini API key (BYOK) set in Settings.
                        </div>
                    </div>
                )}
            </div>

            {/* ── Stats Cards ── */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="stat-card">
                    <div className="label">Total Validations</div>
                    <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                        {loadingStats ? '—' : stats?.totalValidations || 0}
                    </div>
                </div>
                <div className="stat-card" style={{ '--primary-rgb': '34, 197, 94' } as React.CSSProperties}>
                    <div className="label">Passed</div>
                    <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'rgb(var(--success-rgb))', letterSpacing: '-0.02em' }}>
                        {loadingStats ? '—' : stats?.passed || 0}
                    </div>
                </div>
                <div className="stat-card" style={{ '--primary-rgb': '239, 68, 68' } as React.CSSProperties}>
                    <div className="label">Failed</div>
                    <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'rgb(var(--error-rgb))', letterSpacing: '-0.02em' }}>
                        {loadingStats ? '—' : stats?.failed || 0}
                    </div>
                </div>
            </div>

            {/* ── Validate Plan ── */}
            <div className="glass-panel p-6 mb-6">
                <h2 style={{ marginBottom: '1rem' }}>Validate Plan</h2>
                <div className="form-group">
                    <label className="label">Plan JSON (or paste a DFR to view)</label>
                    <textarea
                        className="input"
                        style={{ minHeight: '200px' }}
                        placeholder='Paste your system architecture plan JSON here...'
                        value={planJson}
                        onChange={(e) => setPlanJson(e.target.value)}
                    />
                </div>
                <div className="flex gap-4 items-center flex-wrap">
                    <button
                        className="btn-primary"
                        onClick={handleValidate}
                        disabled={loading || !planJson.trim()}
                    >
                        {loading ? '⏳ Validating...' : '▶ Validate Plan'}
                    </button>

                    <div className="flex items-center gap-2">
                        <span className="text-muted text-xs">Samples:</span>
                        <button className="btn-glass" style={{ fontSize: '0.6875rem', padding: '0.375rem 0.75rem' }}
                            onClick={() => setPlanJson(JSON.stringify(SAMPLE_PLANS.valid, null, 2))}>
                            ✓ Valid
                        </button>
                        <button className="btn-glass" style={{ fontSize: '0.6875rem', padding: '0.375rem 0.75rem' }}
                            onClick={() => setPlanJson(JSON.stringify(SAMPLE_PLANS.violation, null, 2))}>
                            ⚠ Violation
                        </button>
                        <button className="btn-glass" style={{ fontSize: '0.6875rem', padding: '0.375rem 0.75rem' }}
                            onClick={() => setPlanJson(JSON.stringify(SAMPLE_PLANS.complex, null, 2))}>
                            🔥 Multi-Fail
                        </button>
                    </div>
                </div>

                {/* Error Display */}
                {error && (
                    <div className={`alert mt-4 ${error.includes('system_error') ? 'alert-error' : error.includes('compilation_error') ? 'alert-warning' : 'alert-error'}`}>
                        <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8125rem' }}>
                            {error.includes('compilation_error') ? '⚠️ Compilation Failed' :
                                error.includes('system_error') ? '🔥 System Error' :
                                    error.includes('rate_limit') ? '⏱️ Rate Limited' :
                                        error.includes('invalid_api_key') ? '🔑 Invalid API Key' :
                                            '❌ Error'}
                        </div>
                        <div style={{ fontSize: '0.8125rem' }}>
                            {error.replace('compilation_error: ', '').replace('system_error: ', '')}
                        </div>
                    </div>
                )}
            </div>

            {/* ── DFR Result ── */}
            {dfr && (
                <div className="glass-panel p-6 mb-6">
                    <div className="flex justify-between items-center mb-4">
                        <h2>Deterministic Failure Report</h2>
                        <div className="flex gap-2 items-center">
                            {dfr.cache_hit && <span className="badge badge-info">CACHED</span>}
                            <span className={`badge ${dfr.passed ? 'badge-success' : 'badge-error'}`}>
                                {dfr.passed ? 'PASSED' : 'FAILED'}
                            </span>
                        </div>
                    </div>

                    {/* Status Hero */}
                    <div style={{
                        padding: '1.25rem',
                        borderRadius: 'var(--radius-md)',
                        marginBottom: '1.25rem',
                        background: dfr.passed ? 'rgba(var(--success-rgb), 0.05)' : 'rgba(var(--error-rgb), 0.05)',
                        border: `1px solid ${dfr.passed ? 'rgba(var(--success-rgb), 0.2)' : 'rgba(var(--error-rgb), 0.2)'}`,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem'
                    }}>
                        <div style={{
                            width: '2.5rem', height: '2.5rem',
                            borderRadius: '50%',
                            background: dfr.passed ? 'rgb(var(--success-rgb))' : 'rgb(var(--error-rgb))',
                            display: 'grid', placeItems: 'center',
                            color: '#000', fontWeight: 'bold', fontSize: '1.125rem',
                            flexShrink: 0
                        }}>
                            {dfr.passed ? '✓' : '!'}
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1.125rem', color: dfr.passed ? 'rgb(var(--success-rgb))' : 'rgb(var(--error-rgb))' }}>
                                {dfr.passed ? 'ALL RULES PASSED' : `${dfr.violations.length} VIOLATION${dfr.violations.length !== 1 ? 'S' : ''} FOUND`}
                            </div>
                            <div className="text-muted" style={{ marginTop: '0.125rem' }}>
                                Hash: <code style={{ fontSize: '0.6875rem' }}>{dfr.plan_hash?.slice(0, 12)}...</code>
                                {' · '}Engine: <code style={{ fontSize: '0.6875rem' }}>{dfr.engine_version?.slice(0, 12)}...</code>
                            </div>
                        </div>
                    </div>

                    {/* Violations */}
                    {dfr.violations.length > 0 && (
                        <div>
                            <h3 style={{ marginBottom: '0.75rem' }}>Violations</h3>
                            <div className="flex flex-col gap-2">
                                {dfr.violations.map((v, i) => (
                                    <div key={v.id || i} style={{
                                        padding: '0.875rem 1rem',
                                        background: 'rgba(var(--error-rgb), 0.04)',
                                        borderRadius: 'var(--radius-sm)',
                                        border: '1px solid rgba(var(--error-rgb), 0.15)'
                                    }}>
                                        <div className="flex gap-3 items-center" style={{ marginBottom: '0.375rem' }}>
                                            <code style={{ fontWeight: 700, color: 'rgb(var(--error-rgb))', fontSize: '0.75rem' }}>{v.rule_id}</code>
                                            <span className="text-muted text-xs truncate">ID: {v.id}</span>
                                        </div>
                                        <div style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>{v.message}</div>
                                        <div className="text-muted text-xs" style={{ marginTop: '0.25rem' }}>
                                            Node: <code style={{ fontSize: '0.6875rem' }}>{v.offending_node}</code>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* AI Suggestions Button */}
                    {dfr.violations.length > 0 && (
                        <div style={{ marginTop: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <button
                                className="btn-primary"
                                onClick={handleGetSuggestions}
                                disabled={loadingSuggestions}
                            >
                                {loadingSuggestions ? '🤖 Analyzing with Gemini...' : '🤖 Get AI Fix Suggestions'}
                            </button>
                            {!sessionStorage.getItem(SESSION_KEY_NAME) && (
                                <span className="text-muted text-xs">
                                    ⚠ Requires Gemini key — <a href="/settings" style={{ color: 'rgb(var(--primary-rgb))', textDecoration: 'none' }}>set in Settings</a>
                                </span>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* ── AI Suggestions ── */}
            {suggestions.length > 0 && (
                <div className="glass-panel p-6 mb-6">
                    <div className="flex justify-between items-center mb-4">
                        <h2>AI Suggestions</h2>
                        <span className="badge badge-info">{modelUsed || 'Gemini 3 Pro'}</span>
                    </div>
                    <div className="flex flex-col gap-3">
                        {suggestions.map((s, i) => (
                            <div key={i} style={{
                                padding: '1rem',
                                background: 'rgba(var(--primary-rgb), 0.04)',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid rgba(var(--primary-rgb), 0.15)'
                            }}>
                                <div className="flex justify-between items-center mb-2">
                                    <code className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.violation_id}</code>
                                    <span className={`badge ${s.confidence === 'high' ? 'badge-success' : s.confidence === 'medium' ? 'badge-warning' : 'badge-info'}`}>
                                        {s.confidence}
                                    </span>
                                </div>
                                <div style={{ color: '#e2e8f0', fontSize: '0.875rem' }}>{s.suggestion}</div>
                                {s.patches.length > 0 && (
                                    <pre style={{ marginTop: '0.75rem', fontSize: '0.6875rem' }}>
                                        {JSON.stringify(s.patches, null, 2)}
                                    </pre>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── Bottom Grid: Recent + Violations ── */}
            <div className="flex gap-6" style={{ flexWrap: 'wrap' }}>
                <div className="glass-panel p-6" style={{ flex: '2', minWidth: '300px' }}>
                    <h2 style={{ marginBottom: '1.25rem' }}>Recent Activity</h2>
                    <div className="flex flex-col gap-3">
                        {loadingStats && <div className="text-muted">Loading...</div>}
                        {!loadingStats && (!stats?.recentValidations || stats.recentValidations.length === 0) && (
                            <div className="text-muted" style={{ fontStyle: 'italic' }}>No activity yet. Run your first validation above.</div>
                        )}
                        {stats?.recentValidations.map((val) => (
                            <div key={val.id} className="flex justify-between items-center" style={{
                                padding: '0.75rem 1rem',
                                background: 'rgba(255, 255, 255, 0.02)',
                                borderRadius: 'var(--radius-sm)',
                                border: '1px solid var(--border-subtle)'
                            }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>Plan <code style={{ fontSize: '0.6875rem' }}>{val.plan_hash}</code></div>
                                    <div className="text-muted text-xs">{new Date(val.time).toLocaleString()}</div>
                                </div>
                                <span className={`badge ${val.status === 'passed' ? 'badge-success' : 'badge-error'}`}>
                                    {val.status}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="glass-panel p-6" style={{ flex: '1', minWidth: '280px' }}>
                    <h2 style={{ marginBottom: '1.25rem' }}>Top Violations</h2>
                    <div className="flex flex-col gap-3">
                        {loadingStats ? (
                            <div className="text-muted">Loading...</div>
                        ) : (!stats?.ruleFrequency || stats.ruleFrequency.length === 0) ? (
                            <div className="text-muted" style={{ fontStyle: 'italic' }}>No violations recorded.</div>
                        ) : (
                            stats.ruleFrequency.map((item) => (
                                <div key={item.rule} className="flex justify-between items-center" style={{
                                    padding: '0.5rem 0.75rem',
                                    background: 'rgba(var(--error-rgb), 0.04)',
                                    borderRadius: 'var(--radius-sm)',
                                    border: '1px solid rgba(var(--error-rgb), 0.1)'
                                }}>
                                    <code style={{ fontSize: '0.75rem', color: '#fca5a5' }}>{item.rule}</code>
                                    <span className="font-bold">{item.count}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
