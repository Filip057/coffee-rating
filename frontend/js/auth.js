/**
 * Authentication Store
 *
 * Manages authentication state, tokens, and user data
 */

import Config from '/static/js/config.js';

/**
 * Parse JWT token to get payload
 * @param {string} token
 * @returns {Object|null}
 */
function parseJWT(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            atob(base64)
                .split('')
                .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch {
        return null;
    }
}

/**
 * Check if token is expired
 * @param {string} token
 * @returns {boolean}
 */
function isTokenExpired(token) {
    const payload = parseJWT(token);
    if (!payload || !payload.exp) return true;

    // exp is in seconds, Date.now() is in milliseconds
    return payload.exp * 1000 < Date.now();
}

/**
 * Check if token needs refresh (expires within threshold)
 * @param {string} token
 * @returns {boolean}
 */
function shouldRefreshToken(token) {
    const payload = parseJWT(token);
    if (!payload || !payload.exp) return true;

    const expiresAt = payload.exp * 1000;
    return expiresAt - Date.now() < Config.TOKEN_REFRESH_THRESHOLD;
}

/**
 * Get storage based on remember me preference
 * @returns {Storage}
 */
function getStorage() {
    const rememberMe = localStorage.getItem(Config.STORAGE.REMEMBER_ME) === 'true';
    return rememberMe ? localStorage : sessionStorage;
}

const AuthStore = {
    /**
     * Set whether to remember the user
     * @param {boolean} remember
     */
    setRememberMe(remember) {
        localStorage.setItem(Config.STORAGE.REMEMBER_ME, String(remember));
    },

    /**
     * Store authentication tokens
     * @param {string} accessToken
     * @param {string} refreshToken
     */
    setTokens(accessToken, refreshToken) {
        const storage = getStorage();
        storage.setItem(Config.STORAGE.ACCESS_TOKEN, accessToken);
        storage.setItem(Config.STORAGE.REFRESH_TOKEN, refreshToken);
    },

    /**
     * Get access token
     * @returns {string|null}
     */
    getAccessToken() {
        // Check both storages
        return (
            sessionStorage.getItem(Config.STORAGE.ACCESS_TOKEN) ||
            localStorage.getItem(Config.STORAGE.ACCESS_TOKEN)
        );
    },

    /**
     * Get refresh token
     * @returns {string|null}
     */
    getRefreshToken() {
        return (
            sessionStorage.getItem(Config.STORAGE.REFRESH_TOKEN) ||
            localStorage.getItem(Config.STORAGE.REFRESH_TOKEN)
        );
    },

    /**
     * Store user data
     * @param {Object} user
     */
    setUser(user) {
        const storage = getStorage();
        storage.setItem(Config.STORAGE.USER, JSON.stringify(user));
    },

    /**
     * Get stored user data
     * @returns {Object|null}
     */
    getUser() {
        const userData =
            sessionStorage.getItem(Config.STORAGE.USER) ||
            localStorage.getItem(Config.STORAGE.USER);

        if (!userData) return null;

        try {
            return JSON.parse(userData);
        } catch {
            return null;
        }
    },

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated() {
        const token = this.getAccessToken();
        if (!token) return false;

        // Check if access token is expired
        if (isTokenExpired(token)) {
            // Check if we have a valid refresh token
            const refreshToken = this.getRefreshToken();
            return refreshToken && !isTokenExpired(refreshToken);
        }

        return true;
    },

    /**
     * Check if access token needs refresh
     * @returns {boolean}
     */
    needsRefresh() {
        const token = this.getAccessToken();
        if (!token) return false;
        return shouldRefreshToken(token);
    },

    /**
     * Refresh the access token
     * @returns {Promise<boolean>} Whether refresh was successful
     */
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken || isTokenExpired(refreshToken)) {
            return false;
        }

        try {
            const response = await fetch(`${Config.API_BASE_URL}${Config.AUTH.REFRESH}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh: refreshToken }),
            });

            if (!response.ok) {
                return false;
            }

            const data = await response.json();
            this.setTokens(data.access, refreshToken);
            return true;
        } catch {
            return false;
        }
    },

    /**
     * Clear all auth data (logout)
     */
    logout() {
        // Clear from both storages
        const keys = [
            Config.STORAGE.ACCESS_TOKEN,
            Config.STORAGE.REFRESH_TOKEN,
            Config.STORAGE.USER,
        ];

        keys.forEach(key => {
            localStorage.removeItem(key);
            sessionStorage.removeItem(key);
        });
    },

    /**
     * Get user's initials for avatar
     * @returns {string}
     */
    getUserInitials() {
        const user = this.getUser();
        if (!user) return '?';

        if (user.display_name) {
            const parts = user.display_name.split(' ');
            if (parts.length >= 2) {
                return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
            }
            return user.display_name.substring(0, 2).toUpperCase();
        }

        if (user.email) {
            return user.email.substring(0, 2).toUpperCase();
        }

        return '?';
    },

    /**
     * Get user's display name
     * @returns {string}
     */
    getDisplayName() {
        const user = this.getUser();
        if (!user) return 'Uživatel';

        return user.display_name || user.email?.split('@')[0] || 'Uživatel';
    },
};

export default AuthStore;
