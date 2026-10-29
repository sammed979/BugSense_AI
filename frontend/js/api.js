// API Client Module
const API_BASE_URL = 'http://localhost:8000/api/v1';

class APIClient {
    constructor() {
        this.refreshing = false;
    }

    getAccessToken() {
        return localStorage.getItem('access_token');
    }

    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    }

    getAuthHeaders() {
        const token = this.getAccessToken();
        if (token) {
            return {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            };
        }
        return {
            'Content-Type': 'application/json',
        };
    }

    async refreshTokenRequest() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }),
        });

        if (!response.ok) {
            const text = await response.text();
            console.error('Token refresh failed:', response.status, text);
            throw new Error('Token refresh failed');
        }

        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        if (data.refresh) {
            localStorage.setItem('refresh_token', data.refresh);
        }
        return data.access;
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers,
            },
        };

        // Add timeout for long-running requests (like AI repairs)
        const timeout = options.timeout || 60000; // 60 second default
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        config.signal = controller.signal;

        let response = await fetch(url, config);
        clearTimeout(timeoutId);

        // If unauthorized, try to refresh token
        if (response.status === 401 && !this.refreshing) {
            this.refreshing = true;
            try {
                await this.refreshTokenRequest();
                // Retry request with new token
                config.headers = {
                    ...this.getAuthHeaders(),
                    ...options.headers,
                };
                const controller2 = new AbortController();
                const timeoutId2 = setTimeout(() => controller2.abort(), timeout);
                config.signal = controller2.signal;
                response = await fetch(url, config);
                clearTimeout(timeoutId2);
            } catch (error) {
                console.error('Token refresh failed:', error);
                window.auth.clearTokens();
                window.location.hash = '#/login';
                throw error;
            } finally {
                this.refreshing = false;
            }
        }

        return response;
    }

    async login(username, password) {
        const response = await fetch(`${API_BASE_URL}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        const data = await response.json();
        window.auth.setTokens(data.access, data.refresh);
        return data;
    }

    async register(username, email, password) {
        const response = await fetch(`${API_BASE_URL}/auth/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        const data = await response.json();
        window.auth.setTokens(data.access, data.refresh);
        return data;
    }

    async getDashboardStats() {
        const response = await this.request('/dashboard/stats/');
        return response.json();
    }

    async executeCode(payload) {
        const response = await this.request('/execution/execute/', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        return response.json();
    }

    async analyzeCode(payload) {
        const response = await this.request('/analysis/analyze/', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        return response.json();
    }

    async repairCode(payload) {
        const response = await this.request('/repair/', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        return response.json();
    }

    async generateRepair(payload) {
        const response = await this.request('/repair/', {
            method: 'POST',
            body: JSON.stringify(payload),
            timeout: 120000, // 2 minute timeout for AI repairs
        });
        return response.json();
    }

    async repairWithHeuristic(payload) {
        const response = await this.request('/repair/', {
            method: 'POST',
            body: JSON.stringify({ ...payload, use_heuristic: true }),
        });
        return response.json();
    }

    async getHistory() {
        const response = await this.request('/history/');
        return response.json();
    }

    async getSession(sessionId) {
        const response = await this.request(`/history/${sessionId}/`);
        return response.json();
    }
}

window.api = new APIClient();
