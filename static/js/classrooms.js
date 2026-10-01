/**
 * SCRS - Classroom Management Module
 */

async function loadClassroomsData() {
    try {
        // Load Buildings and Facilities if not loaded
        if (state.buildings.length === 0) {
            const bRes = await fetch('/api/buildings');
            if (bRes.ok) state.buildings = await bRes.json();
            populateBuildingDropdowns();
        }
        if (state.facilities.length === 0) {
            const fRes = await fetch('/api/facilities');
            if (fRes.ok) state.facilities = await fRes.json();
        }

        // Fetch classrooms with active filters
        const building = document.getElementById('filter-room-building')?.value || '';
        const type = document.getElementById('filter-room-type')?.value || '';
        const status = document.getElementById('filter-room-status')?.value || '';
        const capacity = document.getElementById('filter-room-capacity')?.value || '';

        let url = `/api/classrooms?building_id=${building}&room_type=${type}&status=${status}&min_capacity=${capacity}`;
        const res = await fetch(url);
        if (res.ok) {
            state.classrooms = await res.json();
            renderClassroomCards(state.classrooms);
        }
    } catch (err) {
        console.error("Failed to load classrooms data:", err);
    }
}

function populateBuildingDropdowns() {
    const selects = [
        document.getElementById('filter-room-building'),
        document.getElementById('filter-res-building'),
        document.getElementById('res-building-select'),
        document.getElementById('edit-room-building'),
        document.getElementById('report-building')
    ];

    selects.forEach(select => {
        if (!select) return;
        const currentVal = select.value;
        const isFilter = select.id.startsWith('filter') || select.id.startsWith('report');
        
        let html = isFilter ? '<option value="">All Buildings</option>' : '<option value="">Select Building...</option>';
        html += state.buildings.map(b => `<option value="${b.building_id}">${b.building_name} (${b.code})</option>`).join('');
        select.innerHTML = html;
        select.value = currentVal;
    });
}

function renderClassroomCards(rooms) {
    const container = document.getElementById('classroom-cards-container');
    if (!container) return;

    if (!rooms || rooms.length === 0) {
        container.innerHTML = '<div class="empty-state">No classrooms found matching criteria.</div>';
        return;
    }

    const isAdmin = state.currentUser?.role === 'Administrator';

    container.innerHTML = rooms.map(room => {
        let statusBadgeClass = 'badge-success';
        if (room.status === 'Under Maintenance') statusBadgeClass = 'badge-warning';
        if (room.status === 'Unavailable') statusBadgeClass = 'badge-danger';

        const facilityPills = (room.facilities || []).map(f => 
            `<span class="facility-pill"><i class="fa-solid ${f.icon || 'fa-check'}"></i> ${f.facility_name}</span>`
        ).join('');

        return `
            <div class="room-card">
                <div class="room-card-header">
                    <div>
                        <div class="room-number-badge">${room.building_code} - ${room.room_number}</div>
                        <small class="text-muted">${room.building_name} • Floor ${room.floor}</small>
                    </div>
                    <span class="badge ${statusBadgeClass}">${room.status}</span>
                </div>
                <div class="room-card-body">
                    <div class="room-spec">
                        <i class="fa-solid fa-users text-muted"></i>
                        <span>Capacity: <strong>${room.capacity} seats</strong></span>
                    </div>
                    <div class="room-spec">
                        <i class="fa-solid fa-layer-group text-muted"></i>
                        <span>Type: <strong>${room.room_type}</strong></span>
                    </div>
                    <div class="facility-pills">
                        ${facilityPills || '<span class="text-muted">Standard Facilities</span>'}
                    </div>
                </div>
                <div class="room-card-footer">
                    ${room.status === 'Available' ? 
                        `<button class="btn btn-primary btn-sm btn-block" onclick="quickReserveRoom(${room.classroom_id}, ${room.building_id})"><i class="fa-solid fa-calendar-plus"></i> Book Room</button>` :
                        `<button class="btn btn-outline btn-sm btn-block" disabled><i class="fa-solid fa-ban"></i> Unavailable</button>`
                    }
                    ${isAdmin ? `
                        <button class="btn btn-outline btn-sm" onclick="editClassroomModal(${room.classroom_id})"><i class="fa-solid fa-pen"></i> Edit</button>
                        <button class="btn btn-danger-light btn-sm" onclick="deleteClassroom(${room.classroom_id})"><i class="fa-solid fa-trash"></i></button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Classroom Filter Event Handlers
['filter-room-building', 'filter-room-type', 'filter-room-status', 'filter-room-capacity'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', loadClassroomsData);
});

// Admin Add/Edit Classroom Modal
document.getElementById('btn-add-classroom')?.addEventListener('click', () => {
    document.getElementById('classroom-modal-title').textContent = 'Add New Classroom';
    document.getElementById('edit-room-id').value = '';
    document.getElementById('form-classroom-edit').reset();
    renderFacilitiesCheckboxes([]);
    openModal('modal-classroom-editor');
});

function renderFacilitiesCheckboxes(selectedIds = []) {
    const container = document.getElementById('edit-facilities-checkboxes');
    if (!container) return;

    container.innerHTML = state.facilities.map(f => `
        <label class="checkbox-label" style="display: flex; align-items: center; gap: 6px; font-size: 0.8125rem;">
            <input type="checkbox" name="facilities" value="${f.facility_id}" ${selectedIds.includes(f.facility_id) ? 'checked' : ''}>
            <span><i class="fa-solid ${f.icon}"></i> ${f.facility_name}</span>
        </label>
    `).join('');
}

async function editClassroomModal(classroomId) {
    try {
        const res = await fetch(`/api/classrooms/${classroomId}`);
        if (res.ok) {
            const room = await res.json();
            document.getElementById('classroom-modal-title').textContent = `Edit Classroom ${room.room_number}`;
            document.getElementById('edit-room-id').value = room.classroom_id;
            document.getElementById('edit-room-number').value = room.room_number;
            document.getElementById('edit-room-building').value = room.building_id;
            document.getElementById('edit-room-floor').value = room.floor;
            document.getElementById('edit-room-capacity').value = room.capacity;
            document.getElementById('edit-room-type').value = room.room_type;
            document.getElementById('edit-room-status').value = room.status;

            const selectedFacIds = (room.facilities || []).map(f => f.facility_id);
            renderFacilitiesCheckboxes(selectedFacIds);
            openModal('modal-classroom-editor');
        }
    } catch (err) {
        console.error("Edit classroom fetch error:", err);
    }
}

document.getElementById('btn-save-classroom')?.addEventListener('click', async () => {
    const roomId = document.getElementById('edit-room-id').value;
    const room_number = document.getElementById('edit-room-number').value.trim();
    const building_id = document.getElementById('edit-room-building').value;
    const floor = document.getElementById('edit-room-floor').value;
    const capacity = document.getElementById('edit-room-capacity').value;
    const room_type = document.getElementById('edit-room-type').value;
    const status = document.getElementById('edit-room-status').value;

    const checkedFacs = Array.from(document.querySelectorAll('input[name="facilities"]:checked')).map(cb => parseInt(cb.value));

    if (!room_number || !building_id || !floor || !capacity || !room_type) {
        alert("Please fill in all required fields.");
        return;
    }

    const payload = { room_number, building_id, floor, capacity, room_type, status, facility_ids: checkedFacs };
    const method = roomId ? 'PUT' : 'POST';
    const url = roomId ? `/api/classrooms/${roomId}` : '/api/classrooms';

    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            closeModal('modal-classroom-editor');
            loadClassroomsData();
        } else {
            alert(data.error || "Failed to save classroom.");
        }
    } catch (err) {
        console.error("Save classroom error:", err);
    }
});

async function deleteClassroom(classroomId) {
    if (!confirm("Are you sure you want to delete this classroom?")) return;
    try {
        const res = await fetch(`/api/classrooms/${classroomId}`, { method: 'DELETE' });
        if (res.ok) {
            loadClassroomsData();
        }
    } catch (err) {
        console.error("Delete classroom error:", err);
    }
}
