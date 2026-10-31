// API Client Module
const FRONTEND_HOST = window.location.hostname;
const API_HOST = ['localhost', '127.0.0.1', '::1'].includes(FRONTEND_HOST) ? '127.0.0.1' : FRONTEND_HOST;
const DEFAULT_API_ORIGIN = `${window.location.protocol}//${API_HOST}:8000`;
const API_BASE_URL = (window.BUGSENSE_API_BASE_URL || `${DEFAULT_API_ORIGIN}/api/v1`).replace(/\/+$/, '');

class APIClient {
    constructor() {
        this.refreshing = null;
        this.learningLessonRequests = new Map();
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

    async fetchWithTimeout(url, options = {}, timeout = 60000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        try {
            return await fetch(url, { ...options, signal: controller.signal });
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('The request timed out. Check that the BugSense backend is running and try again.');
            }
            if (error instanceof TypeError || error.name === 'TypeError') {
                const origin = new URL(API_BASE_URL).origin;
                throw new Error(`Cannot reach the BugSense backend at ${origin}. Start Django from the backend folder with: python manage.py runserver 127.0.0.1:8000`);
            }
            throw new Error('The network request could not be completed. Check your connection and try again.');
        } finally {
            clearTimeout(timeoutId);
        }
    }

    async readResponse(response) {
        try {
            return await response.json();
        } catch {
            return {};
        }
    }

    validationErrorMessage(data, fallback) {
        const safeFields = ['username', 'email', 'password', 'confirm_password', 'non_field_errors', 'detail'];
        const messages = safeFields.flatMap((field) => {
            const value = data && data[field];
            if (typeof value === 'string') return [value];
            if (Array.isArray(value)) return value.filter((item) => typeof item === 'string');
            return [];
        });
        return messages.length ? messages.join(' ') : fallback;
    }

    responseError(response, data, operation) {
        const providerErrors = {
            consent_required: 'Enable source sharing in the workspace before requesting an external AI operation.',
            missing_api_key: 'The selected provider API key is not configured on the backend.',
            authentication: 'The selected provider rejected its configured credentials. Check backend/.env.',
            model_unavailable: 'The configured model is unavailable to this API key.',
            quota_exhausted: 'The selected provider quota is exhausted. Check provider billing or quota.',
            rate_limited: 'The selected provider is rate limiting requests. Wait before trying again.',
            timeout: 'The selected provider did not respond before timeout. Your original code is unchanged.',
            network: 'The selected provider could not be reached. Your original code is unchanged.',
            malformed_response: 'The provider returned a repair that could not be validated. Your original code is unchanged.',
        };
        if (data?.error_type && providerErrors[data.error_type]) return new Error(providerErrors[data.error_type]);
        if (response.status === 401) return new Error('Your session has expired. Please log in again.');
        if (response.status === 403) return new Error('You do not have permission to perform this action.');
        if (response.status === 404) {
            if (operation === 'Lesson') return new Error('This debugging lesson was not found. Refresh the lesson list and choose an available error.');
            return new Error(`${operation} API endpoint was not found. Check that Django is running this project version and restart it from the backend folder.`);
        }
        if (response.status === 413) return new Error('The log is too large. LogSense accepts up to 100,000 characters or a 1 MB text file.');
        if (response.status === 502) return new Error('The AI provider could not complete the explanation request. Your original log remains unchanged.');
        if (response.status === 400) {
            if (operation === 'LogSense' && typeof data?.error === 'string' && data.error.trim()) return new Error(data.error);
            return new Error(this.validationErrorMessage(data, 'Please check the information you entered.'));
        }
        if (response.status >= 500) {
            return new Error(`${operation} is temporarily unavailable. Please try again later.`);
        }
        if (response.status === 429) {
            return new Error('Too many requests. Please wait a moment and try again.');
        }
        return new Error(`${operation} failed. Please check your information and try again.`);
    }

    async refreshTokenRequest() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }),
        });

        if (!response.ok) {
            const error = new Error('Your session expired. Please log in again.');
            error.authExpired = response.status === 400 || response.status === 401;
            throw error;
        }

        const data = await this.readResponse(response);
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
        const timeout = options.timeout || 60000;
        let response = await this.fetchWithTimeout(url, config, timeout);

        if (response.status === 401) {
            if (!this.getRefreshToken()) {
                window.auth.clearTokens();
                window.location.hash = '#/login';
                throw new Error('Your session expired. Please log in again.');
            }
            if (!this.refreshing) {
                this.refreshing = this.refreshTokenRequest().finally(() => { this.refreshing = null; });
            }
            try {
                await this.refreshing;
                config.headers = {
                    ...this.getAuthHeaders(),
                    ...options.headers,
                };
                response = await this.fetchWithTimeout(url, config, timeout);
            } catch (error) {
                if (error.authExpired) {
                    window.auth.clearTokens();
                    window.location.hash = '#/login';
                }
                throw error;
            }
            if (response.status === 401) {
                window.auth.clearTokens();
                window.location.hash = '#/login';
                throw new Error('Your session expired. Please log in again.');
            }
        }

        return response;
    }

    async login(username, password) {
        const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        const data = await this.readResponse(response);
        if (!response.ok) {
            if (response.status === 400 || response.status === 401) {
                throw new Error('The username or password is incorrect.');
            }
            throw this.responseError(response, data, 'Login');
        }

        window.auth.setTokens(data.access, data.refresh);
        return data;
    }

    async register(username, email, password, confirmPassword = password) {
        const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, confirm_password: confirmPassword }),
        });

        const data = await this.readResponse(response);
        if (!response.ok) {
            throw this.responseError(response, data, 'Registration');
        }

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
        const data = await this.readResponse(response);
        if (!response.ok) {
            const error = this.responseError(response, data, 'Execution');
            error.sessionId = data.session_id || null;
            throw error;
        }
        return data;
    }

    async analyzeCode(payload) {
        const response = await this.request('/analysis/analyze/', {
            method: 'POST',
            body: JSON.stringify(payload),
            timeout: 45000,
        });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Analysis');
        return data;
    }

    async explainLog(payload) {
        const response = await this.request('/analysis/logsense/', { method: 'POST', body: JSON.stringify(payload), timeout: 60000 });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'LogSense');
        return data;
    }

    async saveLearningActivity(payload) {
        const response = await this.request('/learning/activities/', { method: 'POST', body: JSON.stringify(payload) });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Learning progress');
        return data;
    }
    async getLearningActivities() {
        const response = await this.request('/learning/activities/');
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Learning history');
        return data;
    }

    async repairCode(payload) {
        const response = await this.request('/repair/', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Repair');
        return data;
    }

    async generateRepair(payload) {
        const response = await this.request('/repair/', {
            method: 'POST',
            body: JSON.stringify(payload),
            timeout: 50000,
        });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Repair');
        return data;
    }

    async getAIProviderSettings() { const r = await this.request('/auth/ai-provider/'); const d = await this.readResponse(r); if (!r.ok) throw this.responseError(r, d, 'Provider settings'); return d; }
    async updateAIProviderSettings(payload) { const r = await this.request('/auth/ai-provider/', { method: 'PATCH', body: JSON.stringify(payload) }); const d = await this.readResponse(r); if (!r.ok) throw this.responseError(r, d, 'Provider settings'); return d; }

    async verifyRepair(payload) {
        const r = await this.request('/verification/', { method: 'POST', body: JSON.stringify(payload), timeout: 15000 });
        const d = await this.readResponse(r);
        if (!r.ok) throw this.responseError(r, d, 'Verification');
        return d;
    }

    async repairWithHeuristic(payload) {
        const response = await this.request('/repair/', {
            method: 'POST',
            body: JSON.stringify({ ...payload, use_heuristic: true }),
        });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Quick Fix');
        return data;
    }

    async getHistory(filters = {}) {
        const query = Object.entries(filters).filter(([, value]) => value !== '' && value !== null && value !== undefined)
            .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join('&');
        const response = await this.request(`/history/${query ? `?${query}` : ''}`);
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'History');
        return data;
    }

    async getSession(sessionId) {
        const response = await this.request(`/history/sessions/${encodeURIComponent(sessionId)}/`);
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Session');
        return data;
    }

    async getLearningTopics(filters = {}) {
        const query = Object.entries(filters).filter(([, value]) => value !== '' && value !== null && value !== undefined).map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join('&');
        const response = await this.request(`/learning/${query ? `?${query}` : ''}`);
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Learning content');
        return data;
    }

    async getLearningDashboard() { return this.learningRequest('/learning/dashboard/'); }
    async getLearningLesson(id) {
        const key = String(id);
        if (this.learningLessonRequests.has(key)) return this.learningLessonRequests.get(key);
        const request = this.learningRequest(`/learning/lessons/${encodeURIComponent(id)}/`, {}, 'Lesson')
            .finally(() => this.learningLessonRequests.delete(key));
        this.learningLessonRequests.set(key, request);
        return request;
    }
    async updateLearningProgress(id, payload) { return this.learningRequest(`/learning/lessons/${encodeURIComponent(id)}/`, {method:'POST',body:JSON.stringify(payload)}); }
    async submitLearningExercise(id, payload) { return this.learningRequest(`/learning/lessons/${encodeURIComponent(id)}/exercise/`, {method:'POST',body:JSON.stringify(payload)}); }
    async submitLearningQuiz(id, answers) { return this.learningRequest(`/learning/lessons/${encodeURIComponent(id)}/quiz/`, {method:'POST',body:JSON.stringify({answers})}); }
    async getLearningRecommendations(payload) { const query=Object.entries(payload).filter(([,value])=>value).map(([key,value])=>`${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join('&'); return this.learningRequest(`/learning/recommendations/${query?`?${query}`:''}`); }
    async learningRequest(endpoint, options = {}, operation = 'Learning') { const response=await this.request(endpoint,options); const data=await this.readResponse(response); if(!response.ok) throw this.responseError(response,data,operation); return data; }

    async getProfile() {
        const response = await this.request('/auth/me/');
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Profile');
        return data;
    }

    async getProjects() {
        const response = await this.request('/projects/');
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Projects');
        return data.projects || [];
    }

    async createProject(payload) {
        const response = await this.request('/projects/', { method: 'POST', body: JSON.stringify(payload) });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Project');
        return data;
    }

    async getProjectFiles(projectId) {
        const response = await this.request(`/projects/${encodeURIComponent(projectId)}/files/`);
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Project files');
        return data.files || [];
    }

    async saveProjectFile(projectId, path, content) {
        const response = await this.request(`/projects/${encodeURIComponent(projectId)}/files/`, { method: 'PUT', body: JSON.stringify({ path, content }) });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Project file');
        return data;
    }

    async updateProfile(payload) {
        const response = await this.request('/auth/me/', { method: 'PATCH', body: JSON.stringify(payload) });
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'Profile');
        return data;
    }

    async getAIHealth() {
        const response = await this.fetchWithTimeout(`${API_BASE_URL}/analysis/health/`, {}, 10000);
        const data = await this.readResponse(response);
        if (!response.ok) throw this.responseError(response, data, 'AI health check');
        return data;
    }
}

window.api = new APIClient();
