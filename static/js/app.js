/**
 * SCRS - Main Application Controller & Router
 */

// Global State Store
const state = {
    currentUser: null,
    activeTab: 'dashboard',
    buildings: [],
    facilities: [],
    departments: [],
    classrooms: [],
    reservations: [],
    users: [],
    notifications: [],
    currentCalDate: new Date()
};

document.addEventListener('DOMContentLoaded', async () => {
    console.log("Initializing Smart Classroom Reservation System...");

    // Set today's date label
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const dateSpan = document.getElementById('current-date-display');
    if (dateSpan) dateSpan.textContent = new Date().toLocaleDateString(undefined, options);

    // Initialize Theme
    initTheme();

    // Check Session Auth
    await checkAuthStatus();

    // Attach Event Listeners
    setupNavigationListeners();
    setupGlobalSearch();
    setupNotificationHandlers();
    setupQuickReserveBtn();
});

function initTheme() {
    const savedTheme = localStorage.getItem('scrs_theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme);

    const themeBtn = document.getElementById('btn-theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('scrs_theme', next);
            updateThemeUI(next);
        });
    }
}

function updateThemeUI(theme) {
    const icon = document.getElementById('theme-icon');
    const text = document.getElementById('theme-text');
    if (icon && text) {
        if (theme === 'dark') {
            icon.className = 'fa-solid fa-sun';
            text.textContent = 'Light Mode';
        } else {
            icon.className = 'fa-solid fa-moon';
            text.textContent = 'Dark Mode';
        }
    }
}

function setupNavigationListeners() {
    // Sidebar nav links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tab = link.getAttribute('data-tab');
            navigateToTab(tab);
        });
    });

    // Sidebar Toggle Mobile
    const toggleBtn = document.getElementById('btn-sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });
    }
}

function navigateToTab(tabName) {
    // Check permission for admin-only tabs
    const adminOnlyTabs = ['approvals', 'reports', 'users', 'buildings'];
    if (adminOnlyTabs.includes(tabName) && state.currentUser?.role !== 'Administrator') {
        alert("Access Denied. This section requires Administrator privileges.");
        return;
    }

    state.activeTab = tabName;

    // Update Sidebar Active state
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('data-tab') === tabName) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // Update Tab Views
    document.querySelectorAll('.tab-view').forEach(view => {
        if (view.id === `view-${tabName}`) {
            view.classList.add('active');
        } else {
            view.classList.remove('active');
        }
    });

    // Trigger tab-specific refresh logic
    if (tabName === 'dashboard') loadDashboardData();
    if (tabName === 'classrooms') loadClassroomsData();
    if (tabName === 'reservations') loadReservationsData();
    if (tabName === 'approvals') loadApprovalsData();
    if (tabName === 'calendar') renderCalendarView();
    if (tabName === 'reports') loadReportsData();
    if (tabName === 'users') loadUsersData();
    if (tabName === 'buildings') loadBuildingsData();
}

function setupGlobalSearch() {
    const input = document.getElementById('global-search');
    if (input) {
        input.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') {
                const query = input.value.trim();
                if (!query) return;
                // Redirect to reservations with search query
                navigateToTab('reservations');
                const statusSelect = document.getElementById('filter-res-status');
                if (statusSelect) statusSelect.value = "";
                loadReservationsData(query);
            }
        });
    }
}

function setupQuickReserveBtn() {
    const btn = document.getElementById('btn-quick-reserve');
    if (btn) {
        btn.addEventListener('click', () => {
            openReservationModal();
        });
    }
}

// Modal Helpers
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'flex';
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}

// Notification Bell Controls
function setupNotificationHandlers() {
    const bellBtn = document.getElementById('btn-notifications');
    const notifMenu = document.getElementById('notif-menu');
    const markReadBtn = document.getElementById('btn-mark-read');

    if (bellBtn && notifMenu) {
        bellBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notifMenu.classList.toggle('show');
        });

        document.addEventListener('click', (e) => {
            if (!notifMenu.contains(e.target) && !bellBtn.contains(e.target)) {
                notifMenu.classList.remove('show');
            }
        });
    }

    if (markReadBtn) {
        markReadBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/notifications/read-all', { method: 'PUT' });
                if (res.ok) {
                    fetchNotifications();
                }
            } catch (err) {
                console.error("Failed to mark notifications read:", err);
            }
        });
    }
}

async function fetchNotifications() {
    if (!state.currentUser) return;
    try {
        const res = await fetch('/api/notifications');
        if (res.ok) {
            const data = await res.json();
            state.notifications = data.notifications || [];
            
            const badge = document.getElementById('notif-badge');
            if (badge) {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
            renderNotificationsList(state.notifications);
        }
    } catch (err) {
        console.error("Failed to fetch notifications:", err);
    }
}

async function markNotificationSingleRead(notifId) {
    try {
        const res = await fetch(`/api/notifications/${notifId}/read`, { method: 'PUT' });
        if (res.ok) {
            fetchNotifications();
        }
    } catch (err) {
        console.error("Failed to mark notification read:", err);
    }
}

function renderNotificationsList(items) {
    const container = document.getElementById('notif-list');
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = '<div class="empty-state">No notifications available.</div>';
        return;
    }

    container.innerHTML = items.map(n => `
        <div class="notif-item ${n.is_read ? '' : 'unread'}" style="display: flex; justify-content: space-between; align-items: flex-start; padding: 8px 12px; border-bottom: 1px solid var(--border-color, #e5e7eb);">
            <div style="flex: 1; padding-right: 8px;">
                <p style="margin: 0; font-size: 0.8125rem; font-weight: ${n.is_read ? '400' : '600'}; color: var(--text-main, #1f2937);">${n.message}</p>
                <small class="text-muted" style="font-size: 0.7rem;">${n.created_at}</small>
            </div>
            ${!n.is_read ? `
                <button class="btn btn-outline btn-xs" title="Mark as read" onclick="event.stopPropagation(); markNotificationSingleRead(${n.notification_id})">
                    <i class="fa-solid fa-check"></i>
                </button>
            ` : ''}
        </div>
    `).join('');
}
