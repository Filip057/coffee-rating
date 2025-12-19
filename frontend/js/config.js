/**
 * Application Configuration
 *
 * Central configuration for API endpoints and app settings
 */

const Config = {
    // API base URL - change for production
    API_BASE_URL: 'http://localhost:8000/api',

    // Auth endpoints
    AUTH: {
        LOGIN: '/auth/login/',
        REGISTER: '/auth/register/',
        LOGOUT: '/auth/logout/',
        REFRESH: '/auth/token/refresh/',
        USER: '/auth/user/',
        UPDATE_PROFILE: '/auth/user/update/',
    },

    // Storage keys
    STORAGE: {
        ACCESS_TOKEN: 'kavarna_access_token',
        REFRESH_TOKEN: 'kavarna_refresh_token',
        USER: 'kavarna_user',
        REMEMBER_ME: 'kavarna_remember_me',
    },

    // Routes
    ROUTES: {
        LOGIN: '/login.html',
        DASHBOARD: '/dashboard.html',
        REGISTER: '/register.html',
    },

    // Token refresh threshold (refresh when less than 5 minutes remaining)
    TOKEN_REFRESH_THRESHOLD: 5 * 60 * 1000,
};

// Freeze config to prevent modifications
Object.freeze(Config);
Object.freeze(Config.AUTH);
Object.freeze(Config.STORAGE);
Object.freeze(Config.ROUTES);

export default Config;
