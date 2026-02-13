
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

/**
 * Settings Page — BYOK & Security Management
 *
 * CRITICAL: API keys are stored in sessionStorage ONLY.
 * - Not sent to server for storage
 * - Cleared when tab closes
 * - Never logged or persisted
 */

const SESSION_KEY_NAME = 'gemini_api_key';

function RecoveryKeySection() {
    const [key, setKey] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [revealed, setRevealed] = useState(false);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        loadKey();
    }, []);

    const loadKey = async () => {
        try {
            const data = await api.getRecoveryKey();
            setKey(data.recovery_key);
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : 'Failed to load recovery key');
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = () => {
        if (key) {
            navigator.clipboard.writeText(key);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    if (loading) {
        return <div className="text-muted" style={{ padding: '1rem 0' }}>Loading security settings...</div>;
    }

    return (
        <div>
            {/* Warning Banner */}
            <div className="alert alert-warning" style={{ marginBottom: '1.25rem', display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '1.25rem', flexShrink: 0 }}>🔐</span>
                <div>
                    <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>Account Recovery Key</div>
                    <div style={{ fontSize: '0.8125rem', lineHeight: '1.5' }}>
                        This key is the <strong>ONLY</strong> way to restore access to your account if you forget your password.
                        We do not store your raw password, so we cannot reset it for you without this key.
                    </div>
                </div>
            </div>

            {key ? (
                <div style={{
                    background: 'rgba(0, 0, 0, 0.25)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.25rem'
                }}>
                    <div className="flex justify-between items-center mb-2">
                        <span className="label" style={{ margin: 0 }}>Your Personal Recovery Key</span>
                        <button
                            onClick={() => setRevealed(!revealed)}
                            className="btn-glass"
                            style={{ fontSize: '0.6875rem', padding: '0.25rem 0.75rem' }}
                        >
                            {revealed ? '🔒 Hide' : '👁 Reveal'}
                        </button>
                    </div>

                    <div className="flex gap-2">
                        <code style={{
                            display: 'block',
                            width: '100%',
                            padding: '0.75rem 1rem',
                            background: 'rgba(0, 0, 0, 0.3)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '1rem',
                            letterSpacing: '0.05em',
                            textAlign: 'center',
                            color: revealed ? '#c4b5fd' : 'var(--text-muted)',
                            filter: revealed ? 'none' : 'blur(6px)',
                            userSelect: revealed ? 'all' : 'none',
                            transition: 'filter 0.2s'
                        }}>
                            {revealed ? key : '••••-••••-••••-••••'}
                        </code>
                        <button
                            onClick={handleCopy}
                            className="btn-glass"
                            style={{ padding: '0.75rem', fontSize: '1rem', flexShrink: 0 }}
                            title="Copy to clipboard"
                        >
                            {copied ? '✅' : '📋'}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="alert alert-error">
                    {error || 'Recovery key not available. Please try refreshing.'}
                </div>
            )}
        </div>
    );
}

export default function SettingsPage() {
    const [apiKey, setApiKey] = useState('');
    const [savedKey, setSavedKey] = useState<string | null>(null);
    const [msg, setMsg] = useState('');

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const stored = sessionStorage.getItem(SESSION_KEY_NAME);
            if (stored) {
                setSavedKey(stored);
            }
        }
    }, []);

    const handleSaveKey = (e: React.FormEvent) => {
        e.preventDefault();
        if (!apiKey.trim()) {
            setMsg('Please enter an API key');
            return;
        }

        sessionStorage.setItem(SESSION_KEY_NAME, apiKey);
        setSavedKey(apiKey);
        setApiKey('');
        setMsg('Key cached for this session only — not saved to server.');
    };

    const handleClearKey = () => {
        sessionStorage.removeItem(SESSION_KEY_NAME);
        setSavedKey(null);
        setMsg('Key cleared from session.');
    };

    const maskKey = (key: string) => {
        if (key.length <= 8) return '****';
        return key.slice(0, 4) + '···' + key.slice(-4);
    };

    return (
        <div style={{ maxWidth: '720px', margin: '0 auto' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1>Settings</h1>
                <p className="text-muted" style={{ marginTop: '0.25rem' }}>Manage your security and AI provider configuration</p>
            </div>

            {/* ── Recovery Key Section ── */}
            <div className="glass-panel p-6 mb-6">
                <h2 style={{ marginBottom: '1.25rem' }}>Security & Recovery</h2>
                <RecoveryKeySection />
            </div>

            {/* ── BYOK Section ── */}
            <div className="glass-panel p-6 mb-6">
                <div className="flex justify-between items-center mb-4">
                    <h2>AI Provider (BYOK)</h2>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <span className="badge badge-info">Gemini 3 Flash</span>
                        <span className="badge badge-warning">2.5 Flash fallback</span>
                    </div>
                </div>

                {/* Session-Only Warning */}
                <div className="alert alert-info" style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: '1.125rem', flexShrink: 0 }}>🔒</span>
                    <div>
                        <div style={{ fontWeight: 600, marginBottom: '0.125rem', fontSize: '0.875rem' }}>Session-Only Storage</div>
                        <div style={{ fontSize: '0.8125rem' }}>
                            Your API key is stored only in this browser tab (sessionStorage).
                            It is <strong>cleared when you close the tab</strong> and <strong>never sent to the server</strong> for storage.
                        </div>
                    </div>
                </div>

                {/* Current Key Status */}
                {savedKey ? (
                    <div className="alert alert-success" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>✓ Session Key Active</div>
                            <div style={{ fontSize: '0.8125rem' }}>
                                Key: <code style={{ fontSize: '0.75rem' }}>{maskKey(savedKey)}</code>
                            </div>
                        </div>
                        <button onClick={handleClearKey} className="btn-danger">
                            Clear Key
                        </button>
                    </div>
                ) : (
                    <div className="alert alert-warning" style={{ marginBottom: '1.5rem' }}>
                        <div style={{ fontWeight: 600 }}>⚠️ No API Key</div>
                        <div style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>
                            Add your Gemini API key below to use AI-powered suggestions on the Dashboard.
                        </div>
                    </div>
                )}

                {/* Add Key Form */}
                <form onSubmit={handleSaveKey}>
                    <div className="form-group" style={{ marginBottom: '0' }}>
                        <label className="label">Gemini API Key</label>
                        <div className="flex gap-3">
                            <input
                                type="password"
                                className="input"
                                placeholder="AIza..."
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                            />
                            <button type="submit" className="btn-primary" style={{ whiteSpace: 'nowrap' }}>
                                Cache Key
                            </button>
                        </div>
                        {msg && (
                            <div className="text-muted" style={{
                                marginTop: '0.75rem',
                                fontSize: '0.8125rem',
                                padding: '0.5rem 0.75rem',
                                background: 'rgba(var(--primary-rgb), 0.05)',
                                borderRadius: 'var(--radius-sm)',
                                border: '1px solid rgba(var(--primary-rgb), 0.1)'
                            }}>
                                {msg}
                            </div>
                        )}
                    </div>
                </form>

                {/* Rate Limits Info */}
                <div style={{
                    marginTop: '1.5rem',
                    padding: '1rem',
                    background: 'rgba(0, 0, 0, 0.2)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)'
                }}>
                    <div className="label" style={{ marginBottom: '0.75rem' }}>Rate Limits (Gemini 3 Flash)</div>
                    <div className="flex gap-6">
                        <div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>15</div>
                            <div className="text-muted text-xs">requests/min</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>1,500</div>
                            <div className="text-muted text-xs">requests/day</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>∞</div>
                            <div className="text-muted text-xs">tokens/min</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── Server Storage Note ── */}
            <div className="glass-panel p-6">
                <div className="flex items-start gap-3">
                    <span style={{ fontSize: '1.125rem' }}>🛡️</span>
                    <div>
                        <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '0.25rem' }}>About Key Security</div>
                        <div className="text-muted" style={{ fontSize: '0.8125rem', lineHeight: '1.6' }}>
                            Your Gemini API key is sent directly from your browser to the backend <strong>per-request only</strong> via encrypted headers.
                            It is <strong>never stored, logged, or persisted</strong> server-side.
                            Server-side KMS-backed storage is available for enterprise deployments.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
