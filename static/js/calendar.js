/**
 * SCRS - Interactive Calendar & Timetable Module
 */

let currentCalMode = 'day'; // day, week, month

function renderCalendarView() {
    const titleDisplay = document.getElementById('cal-title-display');
    const container = document.getElementById('calendar-container');

    if (!container) return;

    const curr = state.currentCalDate;
    
    if (currentCalMode === 'day') {
        const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
        if (titleDisplay) titleDisplay.textContent = curr.toLocaleDateString(undefined, options);
        const dateStr = curr.toISOString().split('T')[0];
        fetchDailyCalendar(dateStr);
    } else if (currentCalMode === 'week') {
        // Find start of week (Sunday or Monday)
        const startOfWeek = new Date(curr);
        const day = startOfWeek.getDay();
        startOfWeek.setDate(startOfWeek.getDate() - day);
        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(endOfWeek.getDate() + 6);

        const options = { month: 'short', day: 'numeric' };
        if (titleDisplay) {
            titleDisplay.textContent = `Week of ${startOfWeek.toLocaleDateString(undefined, options)} - ${endOfWeek.toLocaleDateString(undefined, options)}, ${curr.getFullYear()}`;
        }

        fetchWeeklyCalendar(startOfWeek, endOfWeek);
    } else if (currentCalMode === 'month') {
        const options = { month: 'long', year: 'numeric' };
        if (titleDisplay) titleDisplay.textContent = curr.toLocaleDateString(undefined, options);
        
        fetchMonthlyCalendar(curr.getFullYear(), curr.getMonth() + 1);
    }
}

async function fetchDailyCalendar(dateStr) {
    try {
        const res = await fetch(`/api/reservations?all=true&date=${dateStr}`);
        if (res.ok) {
            const reservations = await res.json();
            buildDailyMatrix(reservations);
        }
    } catch (err) {
        console.error("Daily calendar fetch error:", err);
    }
}

async function fetchWeeklyCalendar(startOfWeek, endOfWeek) {
    try {
        const res = await fetch('/api/reservations?all=true');
        if (res.ok) {
            const allRes = await res.json();
            const startStr = startOfWeek.toISOString().split('T')[0];
            const endStr = endOfWeek.toISOString().split('T')[0];
            const weeklyRes = allRes.filter(r => r.reservation_date >= startStr && r.reservation_date <= endStr);
            buildWeeklyMatrix(weeklyRes, startOfWeek);
        }
    } catch (err) {
        console.error("Weekly calendar fetch error:", err);
    }
}

async function fetchMonthlyCalendar(year, month) {
    try {
        const res = await fetch('/api/reservations?all=true');
        if (res.ok) {
            const allRes = await res.json();
            const monthStr = `${year}-${String(month).padStart(2, '0')}`;
            const monthlyRes = allRes.filter(r => r.reservation_date.startsWith(monthStr));
            buildMonthlyMatrix(monthlyRes, year, month);
        }
    } catch (err) {
        console.error("Monthly calendar fetch error:", err);
    }
}

function buildDailyMatrix(reservations) {
    const container = document.getElementById('calendar-container');
    if (!container) return;

    if (!reservations || reservations.length === 0) {
        container.innerHTML = `
            <div class="empty-state py-5 text-center">
                <i class="fa-regular fa-calendar-xmark text-muted" style="font-size: 3rem;"></i>
                <h4 class="mt-3">No Reservations Scheduled for this Date</h4>
                <p class="text-muted">Classrooms are wide open for bookings.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th style="width: 120px;">Time Slot</th>
                        <th>Classroom & Reserved Purpose</th>
                        <th>User / Role</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${reservations.map(r => {
                        let badgeClass = 'badge-warning';
                        if (r.status === 'Approved') badgeClass = 'badge-success';
                        if (r.status === 'Rejected') badgeClass = 'badge-danger';
                        if (r.status === 'Cancelled') badgeClass = 'badge-secondary';

                        return `
                            <tr>
                                <td><strong>${r.start_time} - ${r.end_time}</strong></td>
                                <td>
                                    <strong>${r.building_code} - Room ${r.room_number}</strong><br>
                                    <span class="text-muted">${r.purpose}</span>
                                </td>
                                <td>
                                    <strong>${r.user_name}</strong><br>
                                    <small class="text-muted">${r.user_role}</small>
                                </td>
                                <td><span class="badge ${badgeClass}">${r.status}</span></td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function buildWeeklyMatrix(reservations, startOfWeek) {
    const container = document.getElementById('calendar-container');
    if (!container) return;

    const days = [];
    for (let i = 0; i < 7; i++) {
        const d = new Date(startOfWeek);
        d.setDate(d.getDate() + i);
        days.push({
            dateStr: d.toISOString().split('T')[0],
            dayName: d.toLocaleDateString(undefined, { weekday: 'short', month: 'numeric', day: 'numeric' })
        });
    }

    container.innerHTML = `
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        ${days.map(d => `<th class="text-center">${d.dayName}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        ${days.map(d => {
                            const dayRes = reservations.filter(r => r.reservation_date === d.dateStr);
                            return `
                                <td style="vertical-align: top; width: 14%; min-height: 120px;">
                                    ${dayRes.length === 0 ? '<small class="text-muted d-block text-center mt-2">No bookings</small>' : 
                                        dayRes.map(r => `
                                            <div class="card p-2 mb-2" style="font-size: 0.75rem; border-left: 3px solid ${r.status === 'Approved' ? '#10B981' : '#F59E0B'};">
                                                <strong>${r.building_code}-${r.room_number}</strong>
                                                <span>${r.start_time}-${r.end_time}</span>
                                                <small class="text-muted truncate">${r.purpose}</small>
                                            </div>
                                        `).join('')
                                    }
                                </td>
                            `;
                        }).join('')}
                    </tr>
                </tbody>
            </table>
        </div>
    `;
}

function buildMonthlyMatrix(reservations, year, month) {
    const container = document.getElementById('calendar-container');
    if (!container) return;

    if (!reservations || reservations.length === 0) {
        container.innerHTML = `
            <div class="empty-state py-5 text-center">
                <i class="fa-regular fa-calendar-xmark text-muted" style="font-size: 3rem;"></i>
                <h4 class="mt-3">No Reservations Found for this Month</h4>
                <p class="text-muted">No classroom reservations recorded for ${year}-${String(month).padStart(2, '0')}.</p>
            </div>
        `;
        return;
    }

    // Group reservations by date
    const grouped = {};
    reservations.forEach(r => {
        if (!grouped[r.reservation_date]) grouped[r.reservation_date] = [];
        grouped[r.reservation_date].push(r);
    });

    const dates = Object.keys(grouped).sort();

    container.innerHTML = `
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th style="width: 120px;">Date</th>
                        <th>Total Bookings</th>
                        <th>Approved</th>
                        <th>Pending</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    ${dates.map(d => {
                        const items = grouped[d];
                        const approved = items.filter(i => i.status === 'Approved').length;
                        const pending = items.filter(i => i.status === 'Pending').length;
                        const rooms = Array.from(new Set(items.map(i => `${i.building_code}-${i.room_number}`))).join(', ');
                        return `
                            <tr>
                                <td><strong>${d}</strong></td>
                                <td><span class="badge badge-secondary">${items.length} Bookings</span></td>
                                <td><span class="badge badge-success">${approved} Approved</span></td>
                                <td><span class="badge badge-warning">${pending} Pending</span></td>
                                <td><small class="text-muted">${rooms}</small></td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// Prev / Next Controls
document.getElementById('cal-prev')?.addEventListener('click', () => {
    if (currentCalMode === 'day') {
        state.currentCalDate.setDate(state.currentCalDate.getDate() - 1);
    } else if (currentCalMode === 'week') {
        state.currentCalDate.setDate(state.currentCalDate.getDate() - 7);
    } else if (currentCalMode === 'month') {
        state.currentCalDate.setMonth(state.currentCalDate.getMonth() - 1);
    }
    renderCalendarView();
});

document.getElementById('cal-next')?.addEventListener('click', () => {
    if (currentCalMode === 'day') {
        state.currentCalDate.setDate(state.currentCalDate.getDate() + 1);
    } else if (currentCalMode === 'week') {
        state.currentCalDate.setDate(state.currentCalDate.getDate() + 7);
    } else if (currentCalMode === 'month') {
        state.currentCalDate.setMonth(state.currentCalDate.getMonth() + 1);
    }
    renderCalendarView();
});

// Mode switch buttons
document.querySelectorAll('[data-cal-view]').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('[data-cal-view]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentCalMode = btn.getAttribute('data-cal-view');
        renderCalendarView();
    });
});
