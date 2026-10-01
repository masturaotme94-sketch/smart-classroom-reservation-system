# Implementation Plan - Smart Classroom Reservation System (SCRS)

The **Smart Classroom Reservation System (SCRS)** is a full-stack, university-grade web management system built using **Python Flask** and **SQLite**. It automates classroom bookings, manages campus facilities, detects scheduling conflicts, handles multi-role approval workflows, displays dynamic calendar schedules, and generates analytical reports with export options.

---

## Confirmed Requirements & Architectural Choices

> [!CHECKMARK]
> **Core Decisions**:
> 1. **Framework & Database**: Python Flask + SQLite DB.
> 2. **Modular Academic Structure**: Clear separation into `routes/`, `database/`, `templates/`, `static/css/`, and `static/js/`.
> 3. **Role-Based Security**: Users access dashboards tailored strictly to their role (`Administrator`, `Faculty Member`, `Student Organization Officer`). Dev Role Switcher is hidden in production mode.
> 4. **Smart Conflict Engine**: Prevent overlapping bookings, display clear conflict message ("This classroom is already reserved during the selected schedule"), and automatically suggest available classrooms for the requested schedule.
> 5. **Classroom Schema**: Room Number, Building, Floor, Capacity, Room Type (`Lecture Room`, `Laboratory`, `Conference Room`), Facilities, Availability Status (`Available`, `Under Maintenance`, `Unavailable`).
> 6. **Reports & Exports**: Filter reports by Date, Building, Classroom, and Reservation Status. Export reports to PDF and Excel (CSV).

---

## Proposed File & Folder Structure

```
c:\Smart Classroom Reservation System (SCRS)\
  ├── app.py                      # Main Flask application & route register
  ├── config.py                   # App configuration & security settings
  ├── requirements.txt            # Python dependencies (Flask, Flask-CORS, Werkzeug)
  ├── database/
  │   ├── db.py                   # SQLite connection manager & helper methods
  │   ├── schema.sql              # Table definitions (Users, Classrooms, Facilities, Reservations, etc.)
  │   └── seed.py                 # Initial campus seed data
  ├── routes/
  │   ├── auth_routes.py          # Authentication, sessions, & RBAC authorization
  │   ├── classroom_routes.py     # Classroom CRUD, facility mapping, status toggle
  │   ├── reservation_routes.py   # Reservation workflow & Smart Conflict Detection algorithm
  │   ├── report_routes.py        # Analytics & filtered report generation API
  │   └── notification_routes.py  # User notifications API
  ├── templates/
  │   └── index.html              # Main HTML5 application shell
  └── static/
      ├── css/
      │   └── style.css           # University Blue & White styling system & Dark mode
      └── js/
          ├── app.js              # SPA navigation, state manager & notifications
          ├── auth.js             # Login flow, RBAC dashboard switcher
          ├── classrooms.js       # Classroom management & modal editor
          ├── reservations.js     # Booking modal, Smart Conflict UI & Approval queue
          ├── calendar.js         # Interactive Daily/Weekly/Monthly calendar matrix
          ├── reports.js          # Chart.js analytics & PDF/Excel exports
          └── dev_tools.js        # Dev mode role switcher (hidden by default)
```

---

## Verification Plan

### Automated & API Verification
- Run `python database/seed.py` to populate SQLite database.
- Run `python app.py` to start Flask server on `http://127.0.0.1:5000`.
- Execute test scripts to verify authentication, conflict detection, and approval workflow.

### Manual UI Verification
- Log in as Administrator, Faculty Member, and Student Organization Officer to confirm strict role-based dashboard views.
- Test double booking attempt to verify conflict alert and room recommendations.
- Test classroom CRUD operations and status updates.
- Test calendar view, dark mode, and report filtering/export.
