
import { Token } from './models';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN_KEY_NAME = 'access_token';

interface RequestOptions extends RequestInit {
    geminiKey?: string;
    headers?: Record<string, string>;
}

class ApiClient {
    private token: string | null = null;

    constructor() {
        // Auto-load token from localStorage on init
        if (typeof window !== 'undefined') {
            this.token = localStorage.getItem(TOKEN_KEY_NAME);
        }
    }

    setToken(token: string) {
        this.token = token;
        if (typeof window !== 'undefined') {
            localStorage.setItem(TOKEN_KEY_NAME, token);
        }
    }

    clearToken() {
        this.token = null;
        if (typeof window !== 'undefined') {
            localStorage.removeItem(TOKEN_KEY_NAME);
        }
    }

    private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
        const token = localStorage.getItem(TOKEN_KEY_NAME);

        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        } as HeadersInit;

        if (token) {
            (headers as any)['Authorization'] = `Bearer ${token}`;
        }

        // Re-add Gemini key header if provided in the options (assuming it's still passed via a custom option)
        // Note: The provided diff removed geminiKey from RequestOptions and the internal handling.
        // To maintain existing functionality for getSuggestions, we need to re-introduce it.
        // If the user intended to remove geminiKey handling entirely, this part should be removed.
        // For now, assuming the user wants to keep the functionality but the diff was focused on 401.
        if ((options as RequestOptions).geminiKey) {
            (headers as any)['X-Gemini-Key'] = (options as RequestOptions).geminiKey;
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));

            // Handle 401 Unauthorized -> Redirect to Login
            // BUT only for actual JWT expiry, NOT for Gemini key errors
            if (response.status === 401 && !endpoint.includes('/auth/token')) {
                const errorType = errorData?.detail?.type || errorData?.detail || '';
                const isGeminiKeyError = typeof errorType === 'object'
                    ? false
                    : errorType.includes('invalid_api_key') || errorType.includes('byok');

                // Only redirect for JWT session expiry, not Gemini/BYOK key issues
                if (!isGeminiKeyError && !endpoint.includes('/api/agent/')) {
                    localStorage.removeItem(TOKEN_KEY_NAME);
                    window.location.href = '/auth/login?error=session_expired';
                    throw new Error('Session expired');
                }
            }

            const error = new Error(
                typeof errorData.detail === 'string'
                    ? errorData.detail
                    : errorData.detail?.message || 'API Request Failed'
            );
            (error as any).response = { data: errorData, status: response.status };
            throw error;
        }

        return response.json();
    }

    // --- Auth ---
    async login(email: string, password: string): Promise<Token> {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/api/auth/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const error: any = new Error(data.detail || 'Login failed');
            error.response = { status: response.status, data };
            throw error;
        }

        return data;
    }

    async signup(email: string, password: string): Promise<any> {
        return this.request<any>('/api/auth/signup', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    }

    async getRecoveryKey(): Promise<{ recovery_key: string }> {
        return this.request<{ recovery_key: string }>('/api/auth/recovery-key');
    }

    async resetPassword(email: string, recoveryKey: string, newPassword: string): Promise<any> {
        return this.request<any>('/api/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({ email, recovery_key: recoveryKey, new_password: newPassword }),
        });
    }

    // --- Validation ---
    async validate(plan: any): Promise<any> {
        return this.request<any>('/api/validate/', {
            method: 'POST',
            body: JSON.stringify(plan),
        });
    }

    async getValidation(planHash: string): Promise<any> {
        return this.request<any>(`/api/validate/${planHash}`);
    }

    // --- Agent ---
    async getSuggestions(request: {
        plan_hash: string;
        engine_version: string;
        dfr_json: any;
        prompt_mode: 'builtin' | 'custom';
        custom_prompt?: string;
    }, geminiKey: string): Promise<any[]> {
        return this.request<any[]>('/api/agent/suggest', {
            method: 'POST',
            body: JSON.stringify(request),
            geminiKey,
        });
    }

    async getSuggestionsWithMeta(request: {
        plan_hash: string;
        engine_version: string;
        dfr_json: any;
        prompt_mode: 'builtin' | 'custom';
        custom_prompt?: string;
    }, geminiKey: string): Promise<{ data: any[]; model: string; fallback: boolean }> {
        const token = localStorage.getItem(TOKEN_KEY_NAME);

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'X-Gemini-Key': geminiKey,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/agent/suggest`, {
            method: 'POST',
            headers,
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const error = new Error(
                typeof errorData.detail === 'string'
                    ? errorData.detail
                    : errorData.detail?.message || 'API Request Failed'
            );
            (error as any).response = { data: errorData, status: response.status };
            throw error;
        }

        const data = await response.json();
        const model = response.headers.get('X-AI-Model') || 'Gemini 3 Pro';
        const fallback = response.headers.get('X-AI-Fallback') === 'true';

        return { data, model, fallback };
    }

    async getStoredSuggestions(planHash: string): Promise<any[]> {
        return this.request<any[]>(`/api/agent/suggestions?plan_hash=${planHash}`);
    }

    // --- BYOK (Status only - no server storage) ---
    async getByokStatus(): Promise<any> {
        return this.request<any>('/api/byok/status');
    }

    logout() {
        this.clearToken();
        // Also clear session storage if you use it directly
        if (typeof window !== 'undefined') {
            sessionStorage.removeItem(TOKEN_KEY_NAME); // Just in case
        }
    }

    // --- Stats ---
    async getStats(): Promise<any> {
        return this.request<any>('/api/validate/stats');
    }
}


export const api = new ApiClient();
