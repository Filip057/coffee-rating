/**
 * Application Configuration
 *
 * Central configuration for API endpoints and app settings
 */

const Config = {
    // API base URL - uses same origin in production
    API_BASE_URL: '/api',

    // Auth endpoints
    AUTH: {
        LOGIN: '/auth/login/',
        REGISTER: '/auth/register/',
        LOGOUT: '/auth/logout/',
        REFRESH: '/auth/token/refresh/',
        USER: '/auth/user/',
        UPDATE_PROFILE: '/auth/user/update/',
    },

    // Groups endpoints
    GROUPS: {
        LIST: '/groups/',
        MY_GROUPS: '/groups/my/',
        DETAIL: (id) => `/groups/${id}/`,
        MEMBERS: (id) => `/groups/${id}/members/`,
        JOIN: (id) => `/groups/${id}/join/`,
        JOIN_BY_CODE: '/groups/join-by-code/',
        LEAVE: (id) => `/groups/${id}/leave/`,
        LIBRARY: (id) => `/groups/${id}/library/`,
    },

    // Reviews/Library endpoints
    REVIEWS: {
        LIST: '/reviews/',
        MY_REVIEWS: '/reviews/my_reviews/',
        LIBRARY: '/reviews/library/',
        ADD_TO_LIBRARY: '/reviews/library/add/',
        BEAN_SUMMARY: (beanId) => `/reviews/bean/${beanId}/summary/`,
    },

    // Purchases endpoints
    PURCHASES: {
        LIST: '/purchases/',
        MY_OUTSTANDING: '/purchases/my_outstanding/',
        DETAIL: (id) => `/purchases/${id}/`,
        SHARES: '/purchases/shares/',
        MARK_PAID: (shareId) => `/purchases/shares/${shareId}/mark_paid/`,
    },

    // Analytics endpoints
    ANALYTICS: {
        DASHBOARD: '/analytics/dashboard/',
        MY_CONSUMPTION: '/analytics/user/consumption/',
        TASTE_PROFILE: '/analytics/user/taste-profile/',
        TOP_BEANS: '/analytics/beans/top/',
    },

    // Beans endpoints
    BEANS: {
        LIST: '/beans/',
        DETAIL: (id) => `/beans/${id}/`,
        ROASTERIES: '/beans/roasteries/',
        ORIGINS: '/beans/origins/',
    },

    // Storage keys
    STORAGE: {
        ACCESS_TOKEN: 'kavarna_access_token',
        REFRESH_TOKEN: 'kavarna_refresh_token',
        USER: 'kavarna_user',
        REMEMBER_ME: 'kavarna_remember_me',
    },

    // Routes (clean URLs)
    ROUTES: {
        // Auth
        LOGIN: '/login',
        REGISTER: '/register',
        
        // Core
        DASHBOARD: '/dashboard',
        // Groups
        GROUP_LIST: '/groups/list/',
        GROUP_CREATE: '/groups/create/',
        GROUP_DETAIL: (id) => `/groups/${id}/`,

        // Library / Reviews
        LIBRARY: '/library/',
        REVIEW_CREATE: '/reviews/create/',
        REVIEW_DETAIL: (id) => `/reviews/${id}`,

        // Beans
        BEANS: '/beans/',
        BEAN_DETAIL: (id) => `/beans/${id}/`,

        // Purchases
        PURCHASES: '/purchases/',
        PURCHASE_CREATE: '/purchases/create/',

        // Profile
        PROFILE: '/profile/',
    },

    // Token refresh threshold (refresh when less than 5 minutes remaining)
    TOKEN_REFRESH_THRESHOLD: 5 * 60 * 1000,
};

// Freeze config to prevent modifications
Object.freeze(Config);
Object.freeze(Config.AUTH);
Object.freeze(Config.GROUPS);
Object.freeze(Config.REVIEWS);
Object.freeze(Config.PURCHASES);
Object.freeze(Config.ANALYTICS);
Object.freeze(Config.BEANS);
Object.freeze(Config.STORAGE);
Object.freeze(Config.ROUTES);

export default Config;
