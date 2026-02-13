
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function SignupPage() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [recoveryKey, setRecoveryKey] = useState<string | null>(null);

    const handleSignup = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setSuccess(false);

        try {
            const result = await api.signup(email, password);
            // SUCCESS: Show recovery key
            if (result.recovery_key) {
                setRecoveryKey(result.recovery_key);
            }
            setSuccess(true);
        } catch (err: any) {
            // Display specific server error
            const message = err.response?.data?.detail || err.message || 'Signup failed';
            setError(typeof message === 'string' ? message : JSON.stringify(message));
        } finally {
            setLoading(false);
        }
    };

    // Removed auto-redirect useEffect to ensure user sees the key

    if (success) {
        return (
            <div className="container flex justify-center items-center" style={{ minHeight: 'calc(100vh - 80px)' }}>
                <div className="glass-panel" style={{ width: '100%', maxWidth: '520px', padding: '2.5rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem', filter: 'grayscale(1)' }}>🎉</div>
                    <h1 style={{ fontSize: '1.75rem', marginBottom: '1rem' }}>Account Created</h1>

                    {recoveryKey && (
                        <div className="text-left" style={{
                            backgroundColor: 'rgba(234, 179, 8, 0.1)',
                            border: '1px solid rgba(234, 179, 8, 0.2)',
                            borderRadius: '0.5rem',
                            padding: '1.5rem',
                            marginBottom: '2rem'
                        }}>
                            <h3 style={{ color: '#facc15', fontWeight: 600, marginBottom: '0.5rem', fontSize: '1rem' }}>
                                Recovery Key Generated
                            </h3>
                            <p className="text-secondary" style={{ marginBottom: '1rem', fontSize: '0.875rem' }}>
                                This key is the <strong>only way</strong> to reset your password. Store it securely off-line.
                            </p>
                            <div className="flex items-center gap-2">
                                <code className="block w-full p-3 rounded font-mono text-lg tracking-wider select-all text-center"
                                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', color: '#fff' }}>
                                    {recoveryKey}
                                </code>
                                <button
                                    onClick={() => navigator.clipboard.writeText(recoveryKey)}
                                    className="btn-glass"
                                    style={{ padding: '0.75rem', minWidth: 'auto' }}
                                    title="Copy to clipboard"
                                >
                                    Copy
                                </button>
                            </div>
                        </div>
                    )}

                    <button
                        onClick={() => router.push('/auth/login')}
                        className="btn-primary"
                        style={{ width: '100%' }}
                    >
                        Proceed to Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="container flex justify-center items-center" style={{ minHeight: 'calc(100vh - 80px)' }}>
            <div className="glass-panel" style={{ width: '100%', maxWidth: '420px', padding: '2.5rem' }}>
                <div className="flex flex-col items-center gap-4" style={{ marginBottom: '2rem' }}>
                    <div className="brand-logo-css" style={{ transform: 'scale(1.5)' }}>
                        <div className="brand-logo-inner"></div>
                    </div>
                    <h1 style={{ fontSize: '1.75rem', margin: 0 }}>Create Account</h1>
                </div>

                {error && (
                    <div style={{
                        color: '#f87171',
                        marginBottom: '1.5rem',
                        textAlign: 'center',
                        fontSize: '0.875rem',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        padding: '1rem',
                        borderRadius: '0.5rem',
                        border: '1px solid rgba(239, 68, 68, 0.2)'
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSignup}>
                    <div className="form-group">
                        <label className="label" htmlFor="email">Email Address</label>
                        <input
                            id="email"
                            type="email"
                            className="input"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@company.com"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="label" htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            className="input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Must be at least 8 characters"
                            required
                            minLength={8}
                        />
                    </div>

                    <button
                        type="submit"
                        className="btn-primary"
                        style={{ width: '100%', marginTop: '1rem', padding: '0.875rem' }}
                        disabled={loading}
                    >
                        {loading ? 'Creating...' : 'Sign Up'}
                    </button>
                </form>

                <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Already have an account? <a href="/auth/login" style={{ color: 'var(--text-scamper)', textDecoration: 'none', fontWeight: 600, marginLeft: '0.25rem' }}>Sign in</a>
                </div>
            </div>
        </div>
    );
}
