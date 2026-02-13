
'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function Header() {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const pathname = usePathname();
    const router = useRouter();

    useEffect(() => {
        const checkAuth = () => {
            if (typeof window !== 'undefined') {
                const token = localStorage.getItem('access_token');
                setIsLoggedIn(!!token);
            }
        };

        checkAuth();
        window.addEventListener('storage', checkAuth);
        window.addEventListener('auth-change', checkAuth);

        return () => {
            window.removeEventListener('storage', checkAuth);
            window.removeEventListener('auth-change', checkAuth);
        };
    }, [pathname]);

    const handleLogout = () => {
        api.logout();
        setIsLoggedIn(false);
        window.dispatchEvent(new Event('auth-change'));
        router.push('/auth/login');
    };

    return (
        <nav className="navbar">
            <Link href={isLoggedIn ? '/dashboard' : '/'} style={{ textDecoration: 'none' }}>
                <div className="nav-brand">
                    <div className="brand-logo-css">
                        <div className="brand-logo-inner"></div>
                    </div>
                    <span className="brand-text">Governance Engine</span>
                    <span style={{
                        fontSize: '0.5625rem',
                        fontWeight: 600,
                        color: 'rgb(var(--primary-rgb))',
                        background: 'rgba(var(--primary-rgb), 0.15)',
                        padding: '0.125rem 0.5rem',
                        borderRadius: '999px',
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase'
                    }}>
                        MVP
                    </span>
                </div>
            </Link>

            <div className="nav-links">
                {isLoggedIn ? (
                    <>
                        <Link href="/dashboard" className={`nav-link ${pathname === '/dashboard' ? 'active' : ''}`}>
                            Dashboard
                        </Link>
                        <Link href="/settings" className={`nav-link ${pathname === '/settings' ? 'active' : ''}`}>
                            Settings
                        </Link>
                        <div className="separator"></div>
                        <button
                            onClick={handleLogout}
                            className="nav-link"
                            style={{
                                color: 'rgb(var(--error-rgb))',
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                font: 'inherit'
                            }}
                        >
                            Logout
                        </button>
                    </>
                ) : (
                    <Link href="/auth/login" className="nav-link" style={{ color: 'rgb(var(--primary-rgb))' }}>
                        Login
                    </Link>
                )}
            </div>
        </nav>
    );
}
