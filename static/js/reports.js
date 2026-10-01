/**
 * SCRS - Reports, Dashboard Analytics & Export Module
 */

let mostUsedChart = null;
let statusPieChart = null;

async function loadDashboardData() {
    try {
        const res = await fetch('/api/reports/summary');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('stat-total-rooms').textContent = data.total_classrooms;
            document.getElementById('stat-avail-rooms').textContent = data.available_classrooms;
            document.getElementById('stat-pending-res').textContent = data.pending_reservations;
            document.getElementById('stat-today-res').textContent = data.today_reservations;
        }

        // Load recent reservations table for dashboard
        const rRes = await fetch('/api/reservations?all=true');
        if (rRes.ok) {
            const items = await rRes.json();
            renderDashboardRecentTable(items.slice(0, 5));
        }
    } catch (err) {
        console.error("Dashboard summary error:", err);
    }
}

function renderDashboardRecentTable(items) {
    const tbody = document.querySelector('#dashboard-recent-table tbody');
    if (!tbody) return;

    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No recent reservations.</td></tr>';
        return;
    }

    tbody.innerHTML = items.map(r => {
        let badgeClass = 'badge-warning';
        if (r.status === 'Approved') badgeClass = 'badge-success';
        if (r.status === 'Rejected') badgeClass = 'badge-danger';
        if (r.status === 'Cancelled') badgeClass = 'badge-secondary';

        return `
            <tr>
                <td><strong>${r.building_code} - ${r.room_number}</strong></td>
                <td>${r.user_name}</td>
                <td>${r.reservation_date} (${r.start_time}-${r.end_time})</td>
                <td>${r.purpose}</td>
                <td><span class="badge ${badgeClass}">${r.status}</span></td>
                <td><button class="btn btn-outline btn-xs" onclick="navigateToTab('reservations')">View</button></td>
            </tr>
        `;
    }).join('');
}

async function loadReportsData() {
    try {
        const res = await fetch('/api/reports/analytics');
        if (res.ok) {
            const analytics = await res.json();
            renderCharts(analytics);
        }
        fetchFilteredReport();
        loadActivityLogs();
    } catch (err) {
        console.error("Reports data error:", err);
    }
}

function renderCharts(analytics) {
    // 1. Most Used Classrooms Bar Chart
    const ctx1 = document.getElementById('chart-most-used')?.getContext('2d');
    if (ctx1) {
        if (mostUsedChart) mostUsedChart.destroy();
        
        const labels = (analytics.most_used_classrooms || []).map(item => `${item.building_code}-${item.room_number}`);
        const counts = (analytics.most_used_classrooms || []).map(item => item.booking_count);

        mostUsedChart = new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: labels.length ? labels : ['No Data'],
                datasets: [{
                    label: 'Approved Reservations',
                    data: counts.length ? counts : [0],
                    backgroundColor: '#3B82F6',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } }
            }
        });
    }

    // 2. Status Distribution Pie Chart
    const ctx2 = document.getElementById('chart-status-pie')?.getContext('2d');
    if (ctx2) {
        if (statusPieChart) statusPieChart.destroy();

        const labels = (analytics.status_distribution || []).map(item => item.status);
        const counts = (analytics.status_distribution || []).map(item => item.count);

        statusPieChart = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: labels.length ? labels : ['None'],
                datasets: [{
                    data: counts.length ? counts : [1],
                    backgroundColor: ['#10B981', '#F59E0B', '#EF4444', '#6B7280']
                }]
            },
            options: {
                responsive: true
            }
        });
    }
}

async function fetchFilteredReport() {
    const start_date = document.getElementById('report-start-date')?.value || '';
    const end_date = document.getElementById('report-end-date')?.value || '';
    const building_id = document.getElementById('report-building')?.value || '';
    const status = document.getElementById('report-status')?.value || '';

    try {
        const res = await fetch(`/api/reports/filtered?start_date=${start_date}&end_date=${end_date}&building_id=${building_id}&status=${status}`);
        if (res.ok) {
            const rows = await res.json();
            renderReportTable(rows);
        }
    } catch (err) {
        console.error("Filtered report fetch error:", err);
    }
}

function renderReportTable(rows) {
    const tbody = document.querySelector('#report-summary-table tbody');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No report data matches current filters.</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(r => `
        <tr>
            <td>#${r.reservation_id}</td>
            <td>${r.reservation_date}</td>
            <td>${r.start_time} - ${r.end_time}</td>
            <td>${r.room_number} (${r.room_type})</td>
            <td>${r.building_name}</td>
            <td>${r.user_name} (${r.user_role})</td>
            <td>${r.purpose}</td>
            <td><span class="badge badge-secondary">${r.status}</span></td>
        </tr>
    `).join('');
}

async function loadActivityLogs() {
    if (state.currentUser?.role !== 'Administrator') return;

    try {
        const res = await fetch('/api/reports/logs');
        if (res.ok) {
            const logs = await res.json();
            renderActivityLogsTable(logs);
        }
    } catch (err) {
        console.error("Failed to load activity logs:", err);
    }
}

function renderActivityLogsTable(logs) {
    const tbody = document.getElementById('activity-logs-table-body');
    if (!tbody) return;

    if (!logs || logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No activity logs recorded.</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(l => `
        <tr>
            <td><strong>#${l.log_id}</strong></td>
            <td><small class="text-muted">${l.created_at || ''}</small></td>
            <td><strong>${l.user_name || 'System / Guest'}</strong> ${l.user_role ? `<small class="badge badge-outline">${l.user_role}</small>` : ''}</td>
            <td><span class="badge badge-primary">${l.action}</span></td>
            <td><span class="text-muted font-sm">${l.details || ''}</span></td>
        </tr>
    `).join('');
}

document.getElementById('btn-apply-report-filters')?.addEventListener('click', fetchFilteredReport);

// Export to Excel (backend download with CSV fallback)
document.getElementById('btn-export-excel')?.addEventListener('click', () => {
    const start_date = document.getElementById('report-start-date')?.value || '';
    const end_date = document.getElementById('report-end-date')?.value || '';
    const building_id = document.getElementById('report-building')?.value || '';
    const status = document.getElementById('report-status')?.value || '';

    const exportUrl = `/api/reports/export/excel?start_date=${start_date}&end_date=${end_date}&building_id=${building_id}&status=${status}`;
    window.location.href = exportUrl;
});

// Export to Printable PDF
document.getElementById('btn-export-pdf')?.addEventListener('click', () => {
    window.print();
});
