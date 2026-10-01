/**
 * SCRS - Buildings Management Module (CRUD, Deletion Protection, and Modal Handlers)
 */

let currentDeletingBuildingId = null;

async function loadBuildingsData() {
    if (state.currentUser?.role !== 'Administrator') return;

    const searchQuery = document.getElementById('search-building')?.value || '';
    const statusFilter = document.getElementById('filter-building-status')?.value || '';

    try {
        const url = `/api/buildings?search=${encodeURIComponent(searchQuery)}&status=${encodeURIComponent(statusFilter)}`;
        const res = await fetch(url);
        if (res.ok) {
            const data = await res.json();
            state.buildings = data;
            renderBuildingsTable(data);
        }
    } catch (err) {
        console.error("Failed to load buildings data:", err);
    }
}

function renderBuildingsTable(buildings) {
    const tbody = document.getElementById('buildings-table-body');
    if (!tbody) return;

    if (!buildings || buildings.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <div class="empty-state">
                        <i class="fa-solid fa-city fa-2x mb-2 text-muted"></i>
                        <p class="text-muted">No buildings found matching the criteria.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = buildings.map(b => {
        const isInactive = b.status === 'Inactive';
        const statusBadge = isInactive 
            ? '<span class="badge badge-secondary">Inactive</span>' 
            : '<span class="badge badge-success">Active</span>';

        const roomBadgeClass = b.total_classrooms > 0 ? 'badge-primary' : 'badge-secondary';

        return `
            <tr>
                <td><strong>#${b.building_id}</strong></td>
                <td>
                    <div class="font-weight-bold" style="font-weight: 600;">${escapeHTML(b.building_name)}</div>
                    ${b.code ? `<small class="badge badge-outline" style="font-size:0.75rem; padding: 2px 6px;">${escapeHTML(b.code)}</small>` : ''}
                </td>
                <td>
                    <i class="fa-solid fa-layer-group text-muted mr-1"></i>
                    ${b.num_floors} ${b.num_floors === 1 ? 'Floor' : 'Floors'}
                </td>
                <td>
                    <span class="badge ${roomBadgeClass}">
                        <i class="fa-solid fa-door-open mr-1"></i> ${b.total_classrooms} ${b.total_classrooms === 1 ? 'Room' : 'Rooms'}
                    </span>
                </td>
                <td>
                    <span class="text-muted font-sm" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${escapeHTML(b.description || '')}">
                        ${escapeHTML(b.description || 'No description provided.')}
                    </span>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-outline btn-xs mr-1" onclick="openEditBuildingModal(${b.building_id})" title="Edit Building">
                            <i class="fa-solid fa-pen-to-square"></i> Edit
                        </button>
                        <button class="btn btn-danger-light btn-xs" onclick="openDeleteBuildingModal(${b.building_id})" title="Delete Building">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openAddBuildingModal() {
    document.getElementById('building-modal-title').textContent = 'Add New Building';
    document.getElementById('form-building').reset();
    document.getElementById('building-id').value = '';
    document.getElementById('building-status').value = 'Active';

    const errAlert = document.getElementById('building-modal-error');
    if (errAlert) errAlert.style.display = 'none';

    openModal('modal-building');
}

async function openEditBuildingModal(buildingId) {
    let building = (state.buildings || []).find(b => b.building_id === buildingId);
    if (!building) {
        try {
            const res = await fetch(`/api/buildings/${buildingId}`);
            if (res.ok) building = await res.json();
        } catch (err) {
            console.error("Error fetching building detail:", err);
        }
    }

    if (!building) {
        alert("Unable to fetch building details.");
        return;
    }

    document.getElementById('building-modal-title').textContent = 'Edit Building';
    document.getElementById('building-id').value = building.building_id;
    document.getElementById('building-name').value = building.building_name || '';
    document.getElementById('building-code').value = building.code || '';
    document.getElementById('building-floors').value = building.num_floors || 1;
    document.getElementById('building-description').value = building.description || '';
    document.getElementById('building-status').value = building.status || 'Active';

    const errAlert = document.getElementById('building-modal-error');
    if (errAlert) errAlert.style.display = 'none';

    openModal('modal-building');
}

document.getElementById('form-building')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const buildingId = document.getElementById('building-id').value;
    const building_name = document.getElementById('building-name').value.trim();
    const code = document.getElementById('building-code').value.trim();
    const num_floors = parseInt(document.getElementById('building-floors').value, 10);
    const description = document.getElementById('building-description').value.trim();
    const status = document.getElementById('building-status').value;

    const errAlert = document.getElementById('building-modal-error');

    if (!building_name) {
        if (errAlert) {
            errAlert.textContent = "Building Name is required.";
            errAlert.style.display = 'block';
        }
        return;
    }

    const payload = { building_name, code, num_floors, description, status };
    const method = buildingId ? 'PUT' : 'POST';
    const url = buildingId ? `/api/buildings/${buildingId}` : '/api/buildings';

    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            closeModal('modal-building');
            loadBuildingsData();
            // Refresh global building dropdowns across system
            if (typeof populateBuildingDropdowns === 'function') {
                populateBuildingDropdowns();
            }
        } else {
            if (errAlert) {
                errAlert.textContent = data.error || 'Failed to save building.';
                errAlert.style.display = 'block';
            }
        }
    } catch (err) {
        console.error("Save building error:", err);
        if (errAlert) {
            errAlert.textContent = "An error occurred while saving building details.";
            errAlert.style.display = 'block';
        }
    }
});

function openDeleteBuildingModal(buildingId) {
    const building = (state.buildings || []).find(b => b.building_id === buildingId);
    if (!building) return;

    currentDeletingBuildingId = buildingId;

    const nameElem = document.getElementById('delete-building-name');
    const roomsElem = document.getElementById('delete-building-rooms-count');
    const warnBox = document.getElementById('delete-building-warning-box');
    const errAlert = document.getElementById('delete-building-modal-error');

    if (nameElem) nameElem.textContent = building.building_name;
    if (roomsElem) roomsElem.textContent = building.total_classrooms || 0;

    if (errAlert) errAlert.style.display = 'none';

    if (warnBox) {
        if (building.total_classrooms > 0) {
            warnBox.style.display = 'block';
            warnBox.innerHTML = `
                <div class="alert alert-warning" style="margin-top: 10px; margin-bottom: 0;">
                    <i class="fa-solid fa-triangle-exclamation mr-1"></i>
                    <strong>Warning:</strong> This building currently has <strong>${building.total_classrooms}</strong> classroom(s) assigned. 
                    Deletion will be prevented by the system.
                </div>
            `;
        } else {
            warnBox.style.display = 'none';
        }
    }

    openModal('modal-delete-building');
}

async function confirmDeleteBuilding() {
    if (!currentDeletingBuildingId) return;

    const errAlert = document.getElementById('delete-building-modal-error');
    if (errAlert) errAlert.style.display = 'none';

    try {
        const res = await fetch(`/api/buildings/${currentDeletingBuildingId}`, {
            method: 'DELETE'
        });

        const data = await res.json();
        if (res.ok) {
            closeModal('modal-delete-building');
            currentDeletingBuildingId = null;
            loadBuildingsData();
            if (typeof populateBuildingDropdowns === 'function') {
                populateBuildingDropdowns();
            }
        } else {
            if (errAlert) {
                errAlert.textContent = data.error || 'Failed to delete building.';
                errAlert.style.display = 'block';
            }
        }
    } catch (err) {
        console.error("Delete building error:", err);
        if (errAlert) {
            errAlert.textContent = "An error occurred while deleting building.";
            errAlert.style.display = 'block';
        }
    }
}

// Utility HTML escaper
function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Attach Search & Filter Listeners for Buildings
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-building');
    const statusSelect = document.getElementById('filter-building-status');

    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                loadBuildingsData();
            }, 300);
        });
    }

    if (statusSelect) {
        statusSelect.addEventListener('change', () => {
            loadBuildingsData();
        });
    }
});
