/**
 * Bottom Navigation & FAB Component
 *
 * Shared navigation functionality for all pages
 */

/**
 * Get the current page identifier based on URL path
 * @returns {string} Page identifier (dashboard, beans, groups, profile, library, purchases)
 */
function getCurrentPage() {
    const path = window.location.pathname;

    if (path === '/dashboard' || path === '/dashboard/') return 'dashboard';
    if (path.startsWith('/beans')) return 'beans';
    if (path.startsWith('/groups')) return 'groups';
    if (path.startsWith('/profile')) return 'profile';
    if (path.startsWith('/library')) return 'library';
    if (path.startsWith('/purchases')) return 'purchases';

    return 'dashboard';
}

/**
 * Generate the bottom navigation HTML
 * @param {string} activePage - The current active page
 * @returns {string} HTML string for the bottom nav
 */
function generateBottomNavHTML(activePage = null) {
    const currentPage = activePage || getCurrentPage();

    return `
    <!-- FAB Overlay -->
    <div class="fab-overlay" id="fabOverlay"></div>

    <!-- FAB Menu -->
    <div class="fab-menu" id="fabMenu">
        <a href="/beans/create/" class="fab-menu-item" id="fabAddBean"><span>☕</span><span>Pridat kavu</span></a>
        <a href="/reviews/create/" class="fab-menu-item" id="fabAddReview"><span>⭐</span><span>Nove hodnoceni</span></a>
        <a href="/purchases/create/" class="fab-menu-item" id="fabAddPurchase"><span>🛒</span><span>Zaznamenat nakup</span></a>
    </div>

    <!-- Bottom Navigation -->
    <nav class="bottom-nav" aria-label="Hlavni navigace">
        <div class="nav-items">
            <a class="nav-item ${currentPage === 'dashboard' ? 'active' : ''}" href="/dashboard" ${currentPage === 'dashboard' ? 'aria-current="page"' : ''}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                    <path d="M9 22V12h6v10"/>
                </svg>
                <span>Domu</span>
            </a>
            <a class="nav-item ${currentPage === 'beans' ? 'active' : ''}" href="/beans/" ${currentPage === 'beans' ? 'aria-current="page"' : ''}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="m21 21-4.35-4.35"/>
                </svg>
                <span>Hledat</span>
            </a>

            <button class="fab" id="fabBtn" aria-label="Rychle akce" aria-expanded="false">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 5v14M5 12h14"/>
                </svg>
            </button>

            <a class="nav-item ${currentPage === 'groups' ? 'active' : ''}" href="/groups/list/" ${currentPage === 'groups' ? 'aria-current="page"' : ''}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
                <span>Skupiny</span>
            </a>
            <a class="nav-item ${currentPage === 'profile' ? 'active' : ''}" href="/profile/" ${currentPage === 'profile' ? 'aria-current="page"' : ''}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                </svg>
                <span>Profil</span>
            </a>
        </div>
    </nav>
    `;
}

/**
 * Initialize the bottom navigation and FAB functionality
 * Call this after adding the nav HTML to the page
 */
function initBottomNav() {
    const fabBtn = document.getElementById('fabBtn');
    const fabMenu = document.getElementById('fabMenu');
    const fabOverlay = document.getElementById('fabOverlay');

    if (!fabBtn || !fabMenu || !fabOverlay) {
        console.warn('Bottom nav elements not found');
        return;
    }

    // Toggle FAB menu
    function toggleFab() {
        const isOpen = fabMenu.classList.contains('open');
        fabBtn.setAttribute('aria-expanded', !isOpen);
        fabMenu.classList.toggle('open');
        fabOverlay.classList.toggle('open');
    }

    function closeFab() {
        fabBtn.setAttribute('aria-expanded', 'false');
        fabMenu.classList.remove('open');
        fabOverlay.classList.remove('open');
    }

    fabBtn.addEventListener('click', toggleFab);
    fabOverlay.addEventListener('click', closeFab);

    // FAB menu items are now links, they'll navigate automatically
    // Close FAB when any menu item is clicked
    const fabMenuItems = fabMenu.querySelectorAll('.fab-menu-item');
    fabMenuItems.forEach(item => {
        item.addEventListener('click', () => {
            closeFab();
        });
    });

    // Close on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && fabMenu.classList.contains('open')) {
            closeFab();
        }
    });
}

/**
 * Inject the bottom navigation into a page
 * @param {string} activePage - Optional active page override
 */
function injectBottomNav(activePage = null) {
    const html = generateBottomNavHTML(activePage);
    document.body.insertAdjacentHTML('beforeend', html);
    initBottomNav();
}

export { generateBottomNavHTML, initBottomNav, injectBottomNav, getCurrentPage };
export default { generateBottomNavHTML, initBottomNav, injectBottomNav, getCurrentPage };
