/**
 * SCRS - Authentication & Role-Based Access Control (RBAC) Module & User Management
 */

async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/me');
        const data = await res.json();

        if (data.authenticated) {
            state.currentUser = data.user;
            closeModal('modal-login');
            updateUserRoleUI();
            fetchNotifications();
            loadDashboardData();
        } else {
            state.currentUser = null;
            openModal('modal-login');
        }
    } catch (err) {
        console.error("Auth check error:", err);
        openModal('modal-login');
    }
}

document.getElementById('form-login')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value.trim();
    const errorAlert = document.getElementById('login-error-alert');

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (res.ok) {
            state.currentUser = data.user;
            if (errorAlert) errorAlert.style.display = 'none';
            closeModal('modal-login');
            updateUserRoleUI();
            fetchNotifications();
            loadDashboardData();
        } else {
            if (errorAlert) {
                errorAlert.textContent = data.error || 'Login failed.';
                errorAlert.style.display = 'block';
            }
        }
    } catch (err) {
        console.error("Login submission error:", err);
    }
});

document.getElementById('btn-logout')?.addEventListener('click', async () => {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        state.currentUser = null;
        window.location.reload();
    } catch (err) {
        console.error("Logout error:", err);
    }
});

function updateUserRoleUI() {
    if (!state.currentUser) return;

    const role = state.currentUser.role;
    const name = state.currentUser.name;

    // Sidebar Profile
    const nameElem = document.getElementById('sidebar-user-name');
    const roleElem = document.getElementById('sidebar-user-role');
    const avatarElem = document.getElementById('user-avatar-initials');

    if (nameElem) nameElem.textContent = name;
    if (roleElem) roleElem.textContent = role;
    if (avatarElem) avatarElem.textContent = name.charAt(0).toUpperCase();

    // Show/Hide Admin-Only Nav Links and Elements
    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(el => {
        if (role === 'Administrator') {
            el.style.display = '';
        } else {
            el.style.display = 'none';
        }
    });

    // Update Reservation page title & button based on role
    const resNavTitle = document.getElementById('nav-res-title');
    const resPageTitle = document.getElementById('res-page-title');

    if (role === 'Administrator') {
        if (resNavTitle) resNavTitle.textContent = 'All Reservations';
        if (resPageTitle) resPageTitle.textContent = 'All System Reservations';
    } else {
        if (resNavTitle) resNavTitle.textContent = 'My Reservations';
        if (resPageTitle) resPageTitle.textContent = 'My Classroom Reservations';
    }
}

function quickFillLogin(email, password) {
    document.getElementById('login-email').value = email;
    document.getElementById('login-password').value = password;
}

// ==========================================
// ==========================================
// MANAGE USERS MODULE (FULL CRUD)
// ==========================================

async function loadUsersData() {
    if (state.currentUser?.role !== 'Administrator') return;

    try {
        // Load Departments if empty
        if (state.departments.length === 0) {
            const dRes = await fetch('/api/auth/departments');
            if (dRes.ok) state.departments = await dRes.json();
            populateDepartmentDropdown();
        }

        const res = await fetch('/api/users');
        if (res.ok) {
            state.users = await res.json();
            renderUsersTable(state.users);
        }
    } catch (err) {
        console.error("Failed to load users data:", err);
    }
}

function populateDepartmentDropdown() {
    const deptSelect = document.getElementById('edit-user-dept');
    if (!deptSelect) return;

    deptSelect.innerHTML = '<option value="">Select Department...</option>' + 
        state.departments.map(d => `<option value="${d.department_id}">${d.department_name}</option>`).join('');
}

function renderUsersTable(users) {
    const tbody = document.querySelector('#users-table tbody');
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No user accounts found.</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(u => {
        let roleBadge = 'badge-secondary';
        if (u.role === 'Administrator') roleBadge = 'badge-danger';
        if (u.role === 'Faculty') roleBadge = 'badge-success';
        if (u.role === 'Student Officer') roleBadge = 'badge-warning';

        return `
            <tr>
                <td><strong>#${u.user_id}</strong></td>
                <td><strong>${u.name}</strong></td>
                <td>${u.email}</td>
                <td><span class="badge ${roleBadge}">${u.role}</span></td>
                <td>${u.department_name || 'N/A'}</td>
                <td>
                    <div class="d-flex gap-1">
                        <button class="btn btn-outline btn-xs" onclick="editUserModal(${u.user_id})">
                            <i class="fa-solid fa-pen"></i> Edit
                        </button>
                        ${u.user_id !== state.currentUser.user_id ? `
                            <button class="btn btn-danger-light btn-xs" onclick="deleteUser(${u.user_id})">
                                <i class="fa-solid fa-trash"></i> Delete
                            </button>
                        ` : '<span class="text-muted font-xs">(Active Session)</span>'}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Add User Button Listener
document.getElementById('btn-add-user')?.addEventListener('click', () => {
    document.getElementById('user-modal-title').innerHTML = '<i class="fa-solid fa-user-plus text-primary"></i> Add User Account';
    document.getElementById('edit-user-id').value = '';
    document.getElementById('form-user-edit').reset();
    document.getElementById('edit-user-password').required = true;
    document.getElementById('user-pw-hint').textContent = '(Required for new users)';
    populateDepartmentDropdown();
    openModal('modal-user-editor');
});

async function editUserModal(userId) {
    try {
        const res = await fetch(`/api/users/${userId}`);
        if (res.ok) {
            const user = await res.json();
            document.getElementById('user-modal-title').innerHTML = `<i class="fa-solid fa-user-pen text-primary"></i> Edit User #${user.user_id}`;
            document.getElementById('edit-user-id').value = user.user_id;
            document.getElementById('edit-user-name').value = user.name;
            document.getElementById('edit-user-email').value = user.email;
            document.getElementById('edit-user-role').value = user.role;
            
            populateDepartmentDropdown();
            document.getElementById('edit-user-dept').value = user.department_id || '';
            document.getElementById('edit-user-password').value = '';
            document.getElementById('edit-user-password').required = false;
            document.getElementById('user-pw-hint').textContent = '(Leave blank to keep current password)';

            openModal('modal-user-editor');
        }
    } catch (err) {
        console.error("Fetch user detail error:", err);
    }
}

document.getElementById('btn-save-user')?.addEventListener('click', async () => {
    const userId = document.getElementById('edit-user-id').value;
    const name = document.getElementById('edit-user-name').value.trim();
    const email = document.getElementById('edit-user-email').value.trim();
    const password = document.getElementById('edit-user-password').value.trim();
    const role = document.getElementById('edit-user-role').value;
    const department_id = document.getElementById('edit-user-dept').value;

    if (!name || !email || !role) {
        alert("Name, email, and role are required.");
        return;
    }

    if (!userId && !password) {
        alert("Password is required for new user creation.");
        return;
    }

    const payload = { name, email, role, department_id, password };
    const method = userId ? 'PUT' : 'POST';
    const url = userId ? `/api/users/${userId}` : '/api/users';

    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            closeModal('modal-user-editor');
            alert(data.message || "User saved successfully.");
            loadUsersData();
        } else {
            alert(data.error || "Failed to save user.");
        }
    } catch (err) {
        console.error("Save user error:", err);
    }
});

async function deleteUser(userId) {
    if (!confirm("Are you sure you want to delete this user account?")) return;
    try {
        const res = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok) {
            loadUsersData();
        } else {
            alert(data.error || "Failed to delete user.");
        }
    } catch (err) {
        console.error("Delete user error:", err);
    }
}

// Forgot Password Modal Controls
document.getElementById('btn-forgot-password')?.addEventListener('click', () => {
    const alertElem = document.getElementById('forgot-pw-alert');
    if (alertElem) alertElem.style.display = 'none';
    const emailElem = document.getElementById('forgot-pw-email');
    if (emailElem) emailElem.value = '';
    openModal('modal-forgot-pw');
});

document.getElementById('form-forgot-pw')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('forgot-pw-email')?.value.trim();
    const alertElem = document.getElementById('forgot-pw-alert');

    if (!email) return;

    try {
        const res = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (alertElem) {
            alertElem.textContent = data.message || data.error;
            alertElem.className = res.ok ? 'alert alert-success' : 'alert alert-danger';
            alertElem.style.display = 'block';
        }
        if (res.ok) {
            setTimeout(() => {
                closeModal('modal-forgot-pw');
            }, 2500);
        }
    } catch (err) {
        console.error("Forgot password error:", err);
        if (alertElem) {
            alertElem.textContent = "An error occurred while submitting request.";
            alertElem.className = 'alert alert-danger';
            alertElem.style.display = 'block';
        }
    }
});
