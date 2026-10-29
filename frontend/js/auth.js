// Authentication Module
const auth = {
    // Store tokens in localStorage
    setTokens(accessToken, refreshToken) {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    },

    // Get access token
    getAccessToken() {
        return localStorage.getItem('access_token');
    },

    // Get refresh token
    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    // Clear tokens
    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    },

    // Check if user is authenticated
    isAuthenticated() {
        return !!this.getAccessToken();
    },

    // Logout
    logout() {
        this.clearTokens();
        window.location.hash = '#/login';
    }
};
