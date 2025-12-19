/**
 * API Service
 *
 * Centralized API client with authentication handling
 */

import Config from './config.js';
import AuthStore from './auth.js';

class ApiError extends Error {
    constructor(status, data) {
        super(data?.error || data?.message || 'An error occurred');
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

/**
 * Make an authenticated API request
 *
 * @param {string} endpoint - API endpoint (relative to base URL)
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function request(endpoint, options = {}) {
    const url = `${Config.API_BASE_URL}${endpoint}`;

    // Default headers
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Add auth token if available
    const token = AuthStore.getAccessToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, {
            ...options,
            headers,
        });

        // Handle 401 - try to refresh token
        if (response.status === 401 && token) {
            const refreshed = await AuthStore.refreshAccessToken();
            if (refreshed) {
                // Retry with new token
                headers['Authorization'] = `Bearer ${AuthStore.getAccessToken()}`;
                const retryResponse = await fetch(url, { ...options, headers });
                return handleResponse(retryResponse);
            } else {
                // Refresh failed, redirect to login
                AuthStore.logout();
                window.location.href = Config.ROUTES.LOGIN;
                throw new ApiError(401, { error: 'Session expired' });
            }
        }

        return handleResponse(response);
    } catch (error) {
        if (error instanceof ApiError) {
            throw error;
        }
        // Network error
        throw new ApiError(0, { error: 'Network error. Please check your connection.' });
    }
}

/**
 * Handle API response
 */
async function handleResponse(response) {
    let data;

    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        throw new ApiError(response.status, data);
    }

    return data;
}

/**
 * API methods organized by resource
 */
const api = {
    /**
     * Authentication endpoints
     */
    auth: {
        /**
         * Login with email and password
         * @param {string} email
         * @param {string} password
         * @returns {Promise<{message: string, user: Object, tokens: {access: string, refresh: string}}>}
         */
        async login(email, password) {
            const data = await request(Config.AUTH.LOGIN, {
                method: 'POST',
                body: JSON.stringify({ email, password }),
            });

            // Store tokens and user
            AuthStore.setTokens(data.tokens.access, data.tokens.refresh);
            AuthStore.setUser(data.user);

            return data;
        },

        /**
         * Register a new account
         * @param {Object} userData - { email, password, password_confirm, display_name? }
         * @returns {Promise<{message: string, user: Object, tokens: Object}>}
         */
        async register(userData) {
            const data = await request(Config.AUTH.REGISTER, {
                method: 'POST',
                body: JSON.stringify(userData),
            });

            // Store tokens and user
            AuthStore.setTokens(data.tokens.access, data.tokens.refresh);
            AuthStore.setUser(data.user);

            return data;
        },

        /**
         * Logout current user
         * @returns {Promise<void>}
         */
        async logout() {
            const refreshToken = AuthStore.getRefreshToken();

            try {
                if (refreshToken) {
                    await request(Config.AUTH.LOGOUT, {
                        method: 'POST',
                        body: JSON.stringify({ refresh: refreshToken }),
                    });
                }
            } finally {
                AuthStore.logout();
            }
        },

        /**
         * Get current user profile
         * @returns {Promise<Object>}
         */
        async getCurrentUser() {
            return request(Config.AUTH.USER);
        },

        /**
         * Update user profile
         * @param {Object} updates - Fields to update
         * @returns {Promise<Object>}
         */
        async updateProfile(updates) {
            const data = await request(Config.AUTH.UPDATE_PROFILE, {
                method: 'PATCH',
                body: JSON.stringify(updates),
            });

            // Update stored user
            AuthStore.setUser(data);

            return data;
        },

        /**
         * Refresh access token
         * @param {string} refreshToken
         * @returns {Promise<{access: string}>}
         */
        async refreshToken(refreshToken) {
            return request(Config.AUTH.REFRESH, {
                method: 'POST',
                body: JSON.stringify({ refresh: refreshToken }),
            });
        },
    },

    // Add more resource endpoints as needed:
    // beans: { ... },
    // reviews: { ... },
    // groups: { ... },
    // purchases: { ... },
};

export { api, ApiError };
export default api;
