/**
 * SCRS - Reservation Management & Smart Conflict Detection Module
 */

async function loadReservationsData(searchQuery = '') {
    try {
        const status = document.getElementById('filter-res-status')?.value || '';
        const date = document.getElementById('filter-res-date')?.value || '';
        const building = document.getElementById('filter-res-building')?.value || '';

        let url = `/api/reservations?status=${status}&date=${date}&building_id=${building}&search=${encodeURIComponent(searchQuery)}`;
        const res = await fetch(url);
        if (res.ok) {
            state.reservations = await res.json();
            renderReservationsTable(state.reservations);
        }
    } catch (err) {
        console.error("Failed to load reservations data:", err);
    }
}

function renderReservationsTable(items) {
    const tbody = document.querySelector('#reservations-table tbody');
    if (!tbody) return;

    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No reservation records found.</td></tr>';
        return;
    }

    const isAdmin = state.currentUser?.role === 'Administrator';
    const currentUserId = state.currentUser?.user_id;

    tbody.innerHTML = items.map(r => {
        let badgeClass = 'badge-warning';
        if (r.status === 'Approved') badgeClass = 'badge-success';
        if (r.status === 'Rejected') badgeClass = 'badge-danger';
        if (r.status === 'Cancelled') badgeClass = 'badge-secondary';

        const canCancel = r.status === 'Pending' || r.status === 'Approved';
        const isOwner = r.user_id === currentUserId || isAdmin;

        return `
            <tr>
                <td><strong>#${r.reservation_id}</strong></td>
                <td>
                    <strong>${r.building_code} - ${r.room_number}</strong><br>
                    <small class="text-muted">${r.building_name}</small>
                </td>
                <td>
                    <i class="fa-regular fa-calendar"></i> ${r.reservation_date}<br>
                    <small class="text-muted"><i class="fa-regular fa-clock"></i> ${r.start_time} - ${r.end_time}</small>
                </td>
                <td>
                    <strong>${r.user_name}</strong><br>
                    <span class="role-badge" style="font-size: 0.65rem;">${r.user_role}</span>
                </td>
                <td>${r.purpose}</td>
                <td><span class="badge ${badgeClass}">${r.status}</span></td>
                <td>
                    <div class="d-flex gap-1">
                        ${r.status === 'Approved' ? `
                            <button class="btn btn-outline btn-xs" onclick="showQRPassModal(${r.reservation_id})">
                                <i class="fa-solid fa-qrcode"></i> QR Pass
                            </button>
                        ` : ''}
                        ${canCancel && isOwner ? `
                            <button class="btn btn-danger-light btn-xs" onclick="cancelReservation(${r.reservation_id})">
                                Cancel
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Approval Queue for Admin
async function loadApprovalsData() {
    try {
        const res = await fetch('/api/reservations?status=Pending&all=true');
        if (res.ok) {
            const pendingItems = await res.json();
            
            // Update pending badge count
            const badge = document.getElementById('pending-count-badge');
            if (badge) badge.textContent = pendingItems.length;

            renderApprovalsTable(pendingItems);
        }
    } catch (err) {
        console.error("Failed to load approval queue:", err);
    }
}

function renderApprovalsTable(items) {
    const tbody = document.querySelector('#approvals-table tbody');
    if (!tbody) return;

    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No pending reservation requests awaiting approval.</td></tr>';
        return;
    }

    tbody.innerHTML = items.map(r => `
        <tr>
            <td><strong>#${r.reservation_id}</strong></td>
            <td>
                <strong>${r.building_code} - ${r.room_number}</strong><br>
                <small class="text-muted">${r.building_name}</small>
            </td>
            <td>
                <strong>${r.user_name}</strong><br>
                <small class="text-muted">${r.user_email} • ${r.user_role}</small>
            </td>
            <td>
                ${r.reservation_date}<br>
                <small class="text-muted">${r.start_time} - ${r.end_time}</small>
            </td>
            <td>${r.purpose}</td>
            <td>
                <div class="d-flex gap-2">
                    <button class="btn btn-primary btn-xs" onclick="updateReservationStatus(${r.reservation_id}, 'Approved')">
                        <i class="fa-solid fa-check"></i> Approve
                    </button>
                    <button class="btn btn-danger-light btn-xs" onclick="rejectReservationPrompt(${r.reservation_id})">
                        <i class="fa-solid fa-xmark"></i> Reject
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function updateReservationStatus(resId, status, rejectionReason = '') {
    try {
        const res = await fetch(`/api/reservations/${resId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, rejection_reason: rejectionReason })
        });
        if (res.ok) {
            loadApprovalsData();
            loadReservationsData();
            fetchNotifications();
        }
    } catch (err) {
        console.error("Status update error:", err);
    }
}

function rejectReservationPrompt(resId) {
    const reason = prompt("Please enter the reason for rejecting this reservation request:");
    if (reason !== null) {
        updateReservationStatus(resId, 'Rejected', reason);
    }
}

async function cancelReservation(resId) {
    if (!confirm("Are you sure you want to cancel this reservation?")) return;
    try {
        const res = await fetch(`/api/reservations/${resId}/cancel`, { method: 'PUT' });
        if (res.ok) {
            loadReservationsData();
            fetchNotifications();
        }
    } catch (err) {
        console.error("Cancel reservation error:", err);
    }
}

// Reservation Modal & Smart Conflict Handling
function openReservationModal() {
    if (!state.currentUser) {
        openModal('modal-login');
        return;
    }

    const form = document.getElementById('form-reservation');
    if (form) form.reset();

    // Default date: Tomorrow
    const tmr = new Date();
    tmr.setDate(tmr.getDate() + 1);
    const tmrStr = tmr.toISOString().split('T')[0];
    document.getElementById('res-date').value = tmrStr;
    document.getElementById('res-start-time').value = '10:00';
    document.getElementById('res-end-time').value = '12:00';

    // Hide conflict warning box
    document.getElementById('conflict-alert-banner').style.display = 'none';
    document.getElementById('smart-recommendations-box').style.display = 'none';

    populateBuildingDropdowns();
    openModal('modal-reservation');
}

// Handle Building Selection Change in Booking Form -> Update Classrooms
document.getElementById('res-building-select')?.addEventListener('change', async (e) => {
    const buildingId = e.target.value;
    const roomSelect = document.getElementById('res-classroom-select');
    if (!roomSelect) return;

    if (!buildingId) {
        roomSelect.innerHTML = '<option value="">Choose Classroom...</option>';
        return;
    }

    try {
        const res = await fetch(`/api/classrooms?building_id=${buildingId}&status=Available`);
        if (res.ok) {
            const rooms = await res.json();
            roomSelect.innerHTML = '<option value="">Choose Classroom...</option>' + 
                rooms.map(r => `<option value="${r.classroom_id}">${r.room_number} (${r.room_type} - Cap: ${r.capacity})</option>`).join('');
        }
    } catch (err) {
        console.error("Room options fetch error:", err);
    }
});

// Quick Reserve Button from Classroom Card
async function quickReserveRoom(classroomId, buildingId) {
    openReservationModal();
    document.getElementById('res-building-select').value = buildingId;

    // Trigger change event to load rooms then select target
    const roomSelect = document.getElementById('res-classroom-select');
    try {
        const res = await fetch(`/api/classrooms?building_id=${buildingId}&status=Available`);
        if (res.ok) {
            const rooms = await res.json();
            roomSelect.innerHTML = '<option value="">Choose Classroom...</option>' + 
                rooms.map(r => `<option value="${r.classroom_id}">${r.room_number} (${r.room_type} - Cap: ${r.capacity})</option>`).join('');
            roomSelect.value = classroomId;
        }
    } catch (err) {
        console.error("Quick reserve setup error:", err);
    }
}

// Submit Reservation Handler
document.getElementById('btn-submit-reservation')?.addEventListener('click', async (e) => {
    e.preventDefault();

    const classroom_id = document.getElementById('res-classroom-select').value;
    const reservation_date = document.getElementById('res-date').value;
    const start_time = document.getElementById('res-start-time').value;
    const end_time = document.getElementById('res-end-time').value;
    const purpose = document.getElementById('res-purpose').value.trim();

    if (!classroom_id || !reservation_date || !start_time || !end_time || !purpose) {
        alert("Please complete all required form fields.");
        return;
    }

    const payload = { classroom_id, reservation_date, start_time, end_time, purpose };

    try {
        const res = await fetch('/api/reservations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.status === 409 && data.conflict) {
            // SMART CONFLICT DETECTED!
            showConflictWarning(data);
        } else if (res.ok) {
            closeModal('modal-reservation');
            alert(data.message || "Reservation submitted successfully.");
            loadReservationsData();
            fetchNotifications();
        } else {
            alert(data.error || "Reservation failed.");
        }
    } catch (err) {
        console.error("Submit reservation error:", err);
    }
});

function showConflictWarning(data) {
    const banner = document.getElementById('conflict-alert-banner');
    const recBox = document.getElementById('smart-recommendations-box');
    const recList = document.getElementById('recommendations-list');

    if (banner) {
        banner.style.display = 'flex';
        document.getElementById('conflict-title').textContent = data.error;
    }

    if (recBox && recList) {
        recBox.style.display = 'block';
        
        const alternatives = data.suggested_classrooms || [];
        if (alternatives.length === 0) {
            recList.innerHTML = '<div class="text-muted">No other available classrooms found for this time slot.</div>';
        } else {
            recList.innerHTML = alternatives.map(room => `
                <div class="rec-item">
                    <div>
                        <strong>${room.building_code} - Room ${room.room_number}</strong> (${room.room_type})<br>
                        <small class="text-muted">${room.building_name} • Capacity: ${room.capacity} seats</small>
                    </div>
                    <button class="btn btn-primary btn-xs" onclick="selectAlternativeRoom(${room.classroom_id}, ${room.building_id})">
                        Select Room
                    </button>
                </div>
            `).join('');
        }
    }
}

async function selectAlternativeRoom(classroomId, buildingId) {
    document.getElementById('res-building-select').value = buildingId;
    
    // Refresh classroom select options for that building
    const roomSelect = document.getElementById('res-classroom-select');
    const res = await fetch(`/api/classrooms?building_id=${buildingId}&status=Available`);
    if (res.ok) {
        const rooms = await res.json();
        roomSelect.innerHTML = '<option value="">Choose Classroom...</option>' + 
            rooms.map(r => `<option value="${r.classroom_id}">${r.room_number} (${r.room_type} - Cap: ${r.capacity})</option>`).join('');
        roomSelect.value = classroomId;
    }

    // Hide alert warning
    document.getElementById('conflict-alert-banner').style.display = 'none';
    document.getElementById('smart-recommendations-box').style.display = 'none';
}

// QR Pass Generator Modal
function showQRPassModal(resId) {
    const res = state.reservations.find(r => r.reservation_id === resId);
    if (!res) return;

    document.getElementById('qr-res-id').textContent = `#${res.reservation_id}`;
    document.getElementById('qr-room').textContent = `${res.building_code} - ${res.room_number}`;
    document.getElementById('qr-schedule').textContent = `${res.reservation_date} (${res.start_time} - ${res.end_time})`;
    document.getElementById('qr-user').textContent = `${res.user_name} (${res.user_role})`;

    const qrContainer = document.getElementById('qrcode-display');
    if (qrContainer) {
        qrContainer.innerHTML = '';
        const qrData = `SCRS-PASS-${res.reservation_id}|${res.room_number}|${res.reservation_date}|${res.user_name}`;
        new QRCode(qrContainer, {
            text: qrData,
            width: 140,
            height: 140
        });
    }

    openModal('modal-qr-pass');
}

// Filter Listeners
['filter-res-status', 'filter-res-date', 'filter-res-building'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', () => loadReservationsData());
});
