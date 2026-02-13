
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isActivationError, setIsActivationError] = useState(false);
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setIsActivationError(false);

        try {
            const token = await api.login(email, password);
            // Store token
            if (typeof window !== 'undefined') {
                localStorage.setItem('access_token', token.access_token);
                api.setToken(token.access_token);
            }
            router.push('/dashboard');
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            const status = err.response?.status;

            // Check for activation error (403)
            if (status === 403 && detail?.includes?.('activated') ||
                (typeof detail === 'string' && detail.includes('activation'))) {
                setIsActivationError(true);
                setError('Account not activated. Check your email for the activation link.');
            } else {
                setError(typeof detail === 'string' ? detail : (err.message || 'Login failed'));
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container flex justify-center items-center" style={{ minHeight: 'calc(100vh - 80px)' }}>
            <div className="glass-panel" style={{ width: '100%', maxWidth: '420px', padding: '2.5rem' }}>
                <div className="flex flex-col items-center gap-4" style={{ marginBottom: '2rem' }}>
                    <div className="brand-logo-css" style={{ transform: 'scale(1.5)' }}>
                        <div className="brand-logo-inner"></div>
                    </div>
                    <h1 style={{ fontSize: '1.75rem', margin: 0 }}>Sign In</h1>
                    <p className="text-secondary" style={{ textAlign: 'center' }}>
                        Welcome back to the Governance Engine
                    </p>
                </div>

                {error && (
                    <div style={{
                        color: isActivationError ? '#fbbf24' : '#f87171',
                        marginBottom: '1.5rem',
                        textAlign: 'center',
                        fontSize: '0.875rem',
                        backgroundColor: isActivationError ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        padding: '1rem',
                        borderRadius: '0.5rem',
                        border: `1px solid ${isActivationError ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`
                    }}>
                        {isActivationError && <span style={{ marginRight: '0.5rem' }}>📧</span>}
                        {error}
                    </div>
                )}

                <form onSubmit={handleLogin}>
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
                        <div className="flex justify-between items-center mb-2">
                            <label className="label" htmlFor="password" style={{ marginBottom: 0 }}>Password</label>
                            <a href="/auth/forgot-password" style={{ fontSize: '0.75rem', color: 'var(--text-scamper)', textDecoration: 'none', fontWeight: 500 }}>
                                Forgot Password?
                            </a>
                        </div>
                        <input
                            id="password"
                            type="password"
                            className="input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="btn-primary"
                        style={{ width: '100%', marginTop: '1rem', padding: '0.875rem' }}
                        disabled={loading}
                    >
                        {loading ? 'Authenticating...' : 'Sign In'}
                    </button>
                </form>

                <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Don't have an account? <a href="/auth/signup" style={{ color: 'var(--text-scamper)', textDecoration: 'none', fontWeight: 600, marginLeft: '0.25rem' }}>Sign up</a>
                </div>
            </div>
        </div>
    );
}
