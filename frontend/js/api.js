/**
 * API Service
 *
 * Centralized API client with authentication handling
 */

import Config from '/static/js/config.js';
import AuthStore from '/static/js/auth.js';

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

    /**
     * Groups endpoints
     */
    groups: {
        /**
         * Get all groups where user is a member
         * @returns {Promise<Array>}
         */
        async getMyGroups() {
            return request(Config.GROUPS.MY_GROUPS);
        },

        /**
         * Get group details
         * @param {string} id - Group ID
         * @returns {Promise<Object>}
         */
        async getGroup(id) {
            return request(Config.GROUPS.DETAIL(id));
        },

        /**
         * Get group members
         * @param {string} id - Group ID
         * @returns {Promise<Array>}
         */
        async getMembers(id) {
            return request(Config.GROUPS.MEMBERS(id));
        },

        /**
         * Join a group with invite code
         * @param {string} id - Group ID
         * @param {string} inviteCode - Invite code
         * @returns {Promise<Object>}
         */
        async join(id, inviteCode) {
            return request(Config.GROUPS.JOIN(id), {
                method: 'POST',
                body: JSON.stringify({ invite_code: inviteCode }),
            });
        },

        /**
         * Join a group using only invite code
         * @param {string} inviteCode - Invite code
         * @returns {Promise<Object>}
         */
        async joinByCode(inviteCode) {
            return request(Config.GROUPS.JOIN_BY_CODE, {
                method: 'POST',
                body: JSON.stringify({ invite_code: inviteCode }),
            });
        },

        /**
         * Leave a group
         * @param {string} id - Group ID
         * @returns {Promise<void>}
         */
        async leave(id) {
            return request(Config.GROUPS.LEAVE(id), {
                method: 'POST',
            });
        },

        /**
         * Get group library
         * @param {string} id - Group ID
         * @returns {Promise<Array>}
         */
        async getLibrary(id) {
            return request(Config.GROUPS.LIBRARY(id));
        },

        /**
         * Add a bean to group library
         * @param {string} groupId - Group ID
         * @param {string} beanId - Bean ID
         * @returns {Promise<Object>}
         */
        async addToLibrary(groupId, beanId) {
            return request(Config.GROUPS.LIBRARY(groupId), {
                method: 'POST',
                body: JSON.stringify({ coffeebean_id: beanId }),
            });
        },

        /**
         * Create a new group
         * @param {Object} data - { name, description? }
         * @returns {Promise<Object>}
         */
        async create(data) {
            return request(Config.GROUPS.LIST, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },

        /**
         * List all groups
         * @returns {Promise<Array>}
         */
        async list() {
            return request(Config.GROUPS.LIST);
        },
    },

    /**
     * Reviews/Library endpoints
     */
    reviews: {
        /**
         * Get user's coffee library
         * @param {Object} options - { archived?: boolean, search?: string }
         * @returns {Promise<Array>}
         */
        async getLibrary(options = {}) {
            const params = new URLSearchParams();
            if (options.archived) params.append('archived', 'true');
            if (options.search) params.append('search', options.search);

            const query = params.toString();
            const endpoint = query ? `${Config.REVIEWS.LIBRARY}?${query}` : Config.REVIEWS.LIBRARY;
            return request(endpoint);
        },

        /**
         * Add a bean to library
         * @param {string} beanId - Coffee bean ID
         * @returns {Promise<Object>}
         */
        async addToLibrary(beanId) {
            return request(Config.REVIEWS.ADD_TO_LIBRARY, {
                method: 'POST',
                body: JSON.stringify({ bean_id: beanId }),
            });
        },

        /**
         * Get user's reviews
         * @returns {Promise<Array>}
         */
        async getMyReviews() {
            const data = await request(Config.REVIEWS.MY_REVIEWS);
            // Handle paginated response
            return Array.isArray(data) ? data : (data.results || []);
        },

        /**
         * Get user's reviews count
         * @returns {Promise<number>}
         */
        async getMyReviewsCount() {
            const data = await request(`${Config.REVIEWS.MY_REVIEWS}?page_size=1`);
            // Paginated response includes count
            return data.count ?? (Array.isArray(data) ? data.length : 0);
        },
    },

    /**
     * Purchases endpoints
     */
    purchases: {
        /**
         * Get outstanding payments for current user
         * @returns {Promise<{total_outstanding: number, count: number, shares: Array}>}
         */
        async getOutstanding() {
            return request(Config.PURCHASES.MY_OUTSTANDING);
        },

        /**
         * Get all purchases
         * @param {Object} options - { group?: string }
         * @returns {Promise<Array>}
         */
        async list(options = {}) {
            const params = new URLSearchParams();
            if (options.group) params.append('group', options.group);

            const query = params.toString();
            const endpoint = query ? `${Config.PURCHASES.LIST}?${query}` : Config.PURCHASES.LIST;
            return request(endpoint);
        },

        /**
         * Create a new purchase
         * @param {Object} data - { coffeebean, group?, total_price_czk, weight_grams?, notes? }
         * @returns {Promise<Object>}
         */
        async create(data) {
            return request(Config.PURCHASES.LIST, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },
    },

    /**
     * Analytics endpoints
     */
    analytics: {
        /**
         * Get dashboard summary
         * @returns {Promise<{consumption: Object, taste_profile: Object, top_beans: Array}>}
         */
        async getDashboard() {
            return request(Config.ANALYTICS.DASHBOARD);
        },

        /**
         * Get user's consumption stats
         * @param {Object} options - { start_date?: string, end_date?: string }
         * @returns {Promise<Object>}
         */
        async getConsumption(options = {}) {
            const params = new URLSearchParams();
            if (options.start_date) params.append('start_date', options.start_date);
            if (options.end_date) params.append('end_date', options.end_date);

            const query = params.toString();
            const endpoint = query ? `${Config.ANALYTICS.MY_CONSUMPTION}?${query}` : Config.ANALYTICS.MY_CONSUMPTION;
            return request(endpoint);
        },

        /**
         * Get user's taste profile
         * @returns {Promise<Object>}
         */
        async getTasteProfile() {
            return request(Config.ANALYTICS.TASTE_PROFILE);
        },

        /**
         * Get top beans
         * @param {Object} options - { metric?: string, period?: number, limit?: number }
         * @returns {Promise<Object>}
         */
        async getTopBeans(options = {}) {
            const params = new URLSearchParams();
            if (options.metric) params.append('metric', options.metric);
            if (options.period) params.append('period', options.period.toString());
            if (options.limit) params.append('limit', options.limit.toString());

            const query = params.toString();
            const endpoint = query ? `${Config.ANALYTICS.TOP_BEANS}?${query}` : Config.ANALYTICS.TOP_BEANS;
            return request(endpoint);
        },
    },

    /**
     * Beans endpoints
     */
    beans: {
        /**
         * Get all beans
         * @param {Object} options - { search?: string }
         * @returns {Promise<Array>}
         */
        async list(options = {}) {
            const params = new URLSearchParams();
            if (options.search) params.append('search', options.search);

            const query = params.toString();
            const endpoint = query ? `${Config.BEANS.LIST}?${query}` : Config.BEANS.LIST;
            const data = await request(endpoint);
            // Handle paginated response
            return Array.isArray(data) ? data : (data.results || []);
        },

        /**
         * Get beans count (without fetching all data)
         * @returns {Promise<number>}
         */
        async count() {
            const data = await request(`${Config.BEANS.LIST}?page_size=1`);
            // Paginated response includes count
            return data.count || (Array.isArray(data) ? data.length : 0);
        },

        /**
         * Get bean details
         * @param {string} id - Bean ID
         * @returns {Promise<Object>}
         */
        async get(id) {
            return request(Config.BEANS.DETAIL(id));
        },
    },
};

export { api, ApiError };
export default api;
