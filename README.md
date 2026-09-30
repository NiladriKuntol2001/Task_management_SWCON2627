# Smart Student Task Manager

A web app where students manage assignments, exams, and projects. The system
scores each task's priority from its deadline, difficulty, and estimated time,
classifies it (Low/Medium/High/Critical), and recommends what to work on next.

Built to the exact spec in `claude/requirements-spec.md` (FR-01 through FR-21,
NFR-01 through NFR-14, and the fixed priority formula in Section 3), plus an
**admin panel** (v1.1) for managing every user and task, which is an addition
beyond that spec — see [Admin panel](#admin-panel-v11).

## Stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL, JWT auth (python-jose),
  bcrypt password hashing (passlib), Alembic migrations, pytest test suite.
- **Frontend:** React + TypeScript (Vite), React Router, plain `fetch`-based
  API client, no external UI framework (hand-rolled responsive CSS).
- **Infra:** Docker Compose (Postgres + backend + frontend/nginx).

## Project layout

```
backend/
  app/
    main.py          FastAPI app, CORS, error handling
    models.py         SQLAlchemy models: User, Task
    schemas.py        Pydantic request/response schemas + validation
    priority.py        Priority formula (Section 3 of the spec)
    security.py        Password hashing + JWT
    deps.py             Auth dependencies (get_current_user, require_admin)
    task_service.py     Shared task helpers (overdue, sorting, live priority refresh)
    seed.py             Bootstrap/promote an admin account
    routers/
      auth.py           /auth: register, login, logout, me
      tasks.py          /tasks: CRUD, filter, sort, upcoming, complete
      dashboard.py      /dashboard: student summary + recommendation
      admin.py          /admin: platform stats, all users, all tasks
  alembic/               DB migrations (0001 initial, 0002 admin roles)
  tests/                 pytest suite (auth, tasks, priority, dashboard, admin)
frontend/
  src/
    api/client.ts        Typed fetch client (student + admin APIs)
    context/AuthContext.tsx
    pages/                Login, Register, Dashboard, Tasks, Task form/detail
    pages/admin/          Admin overview, Users, User detail, All tasks
    components/           Navbar, TaskCard, PriorityBadge, StatTile, Modal, route guards
    components/charts/    Dependency-free SVG/HTML charts with tooltips + table view
    components/admin/     User/task edit modals, admin task table
docker-compose.yml
```

## Running it

### Option A — Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env      # edit SECRET_KEY and ADMIN_PASSWORD
ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='a-strong-password' docker compose up --build
```

The admin account is created on first startup from `ADMIN_EMAIL` /
`ADMIN_PASSWORD` (defaults exist in `docker-compose.yml` for local use only —
override them).

- Frontend: http://localhost:3000
- Backend API docs (Swagger): http://localhost:8000/docs

### Option B — run locally

Backend (needs Python 3.12 and a running PostgreSQL, or point `DATABASE_URL`
at any Postgres instance):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL / SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env   # points at http://localhost:8000 by default
npm install
npm run dev
```

### Running the tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

> **Note on this build (v1.0 and v1.1):** the sandbox this project was generated in has no
> outbound access to PyPI or the npm registry, so `pip install` / `npm install`
> and the resulting `pytest` / `npm run build` could not be executed here to
> confirm a green run. The code was written and reviewed carefully against the
> spec (see the traceability table below and the inline `FR-xx`/`NFR-xx`
> comments throughout `backend/app/`), but please run `pytest` and
> `npm run build` yourselves as the first step after cloning — that's also
> the human-review step NFR-14 asks for.

## Admin panel (v1.1)

Log in with the admin account and you land on **/admin**. Admins can still use
the normal student pages (link in the nav bar).

| Page | What it does |
|---|---|
| **Overview** `/admin` | KPI tiles (students, open tasks + hours, completion rate, overdue, critical open, accounts) that each link to the filtered list behind them; 14-day created-vs-completed trend; open tasks by priority, by deadline band (the spec's bands), by difficulty, and by subject; "students who need attention" (most overdue / critical work); latest tasks feed. Every chart has hover tooltips and a Table toggle. |
| **Users** `/admin/users` | Every account with its user ID (click to copy), role, status, open/done/overdue counts, last activity. Search by name, email or ID; filter by role/status; sort. Add, edit (name, email, role, active, password reset) and delete users. |
| **User detail** `/admin/users/:id` | One student's stats and all their tasks, with edit / complete / delete per task. |
| **All tasks** `/admin/tasks` | Every task from every student, with search, subject/status/priority/overdue filters, sorting and pagination. Edit, complete/reopen or delete any task (priority is recalculated). |

**Safety rules (enforced by the API, not just the UI):**
- Every `/admin` endpoint returns 403 for non-admins. Registration can never create an admin.
- An admin can't demote, deactivate or delete themselves, and the last active admin can't be removed.
- Deactivating a user blocks login and invalidates their existing token, but keeps their data (safer than deleting).
- Deleting a user deletes their tasks, behind a confirmation dialog that states how many.

User IDs themselves are immutable UUIDs (other records reference them); "editing a user" changes the account's details, not its ID.

To make another admin later: promote them from the Users page, or run
`python -m app.seed someone@example.com 'password' "Name"` in the backend.

### Also changed in v1.1

- **Live priority:** deadline urgency depends on today's date, so stored scores went stale as deadlines approached. Scores for open tasks are now recomputed on every read (list, detail, dashboard, admin), so sorting and the recommendation always reflect current urgency.
- **Richer student dashboard:** a prominent "What should I work on today?" card with the reason (due when, difficulty, hours), KPI tiles incl. hours due this week and completion %, open work split by priority, an "Up next" queue, and overdue/upcoming lists.
- **Bug fixes from v1.0:** added the missing `email-validator` dependency (needed by `EmailStr`); the test DB now uses a shared in-memory SQLite connection (`StaticPool`) so the TestClient sees the same tables; `tests/` is a package so `tests.conftest` isn't imported twice; deadline comparisons handle naive datetimes from SQLite.
- Tasks now record `completed_at` (migration 0002 backfills it) to power the completions trend.

## Priority formula (Section 3 of the spec — implemented exactly, unmodified)

`Priority Score = Deadline Score × 0.50 + Difficulty Score × 0.30 + Time Score × 0.20`

| Deadline score | Difficulty score | Time score |
|---|---|---|
| >14 days → 10 | Easy → 20 | min(hours × 10, 100) |
| 7–14 days → 25 | Medium → 50 | |
| 3–6 days → 50 | Hard → 80 | |
| 1–2 days → 75 | Very Hard → 100 | |
| <24h or overdue → 100 | | |

Classification: 80–100 Critical · 60–79 High · 40–59 Medium · 0–39 Low.
See `backend/app/priority.py` and `backend/tests/test_priority.py`.

## Requirements traceability

### Functional requirements

| ID | Requirement | Where implemented |
|---|---|---|
| FR-01 | User registration | `POST /auth/register` (`routers/auth.py`) |
| FR-02 | User login | `POST /auth/login` |
| FR-03 | User logout | `POST /auth/logout` |
| FR-04 | Create task | `POST /tasks` (`routers/tasks.py`) |
| FR-05 | Task fields: title, subject, deadline, difficulty, hours | `models.Task`, `schemas.TaskCreate` |
| FR-06 | Edit own task | `PATCH /tasks/{id}` scoped to `owner_id` |
| FR-07 | Delete own task | `DELETE /tasks/{id}` scoped to `owner_id` |
| FR-08 | Mark complete | `POST /tasks/{id}/complete` |
| FR-09 | View task details | `GET /tasks/{id}` |
| FR-10 | Validate before saving | `schemas.py` (`Field`/`field_validator`), 422 responses |
| FR-11 | Calculate priority | `priority.compute_priority` |
| FR-12 | Priority classification | `priority.classify_priority` |
| FR-13 | Recalculate on change | `tasks.update_task`, re-runs `compute_priority` when deadline/difficulty/hours change |
| FR-14 | Tie-break by earlier deadline | sort keys `(-priority_score, deadline)` in `tasks.list_tasks` and `dashboard.get_dashboard` |
| FR-15 | Filter by subject/completion | `GET /tasks?subject=&completed=` |
| FR-16 | Sort by priority/deadline | `GET /tasks?sort_by=` |
| FR-17 | Upcoming deadlines | `GET /tasks/upcoming` |
| FR-18 | Overdue tasks | `GET /tasks?overdue_only=true`, `is_overdue` field |
| FR-19 | Dashboard | `GET /dashboard` |
| FR-20 | "What should I work on today?" | `dashboard.get_dashboard` → `recommended_task` |
| FR-21 | User task access / isolation | every task query filters `owner_id == current_user.id` |

### Non-functional requirements

| ID | Requirement | Where addressed |
|---|---|---|
| NFR-01/02 | Fast responses | Lightweight FastAPI/SQLAlchemy queries, no N+1 patterns |
| NFR-03 | No plaintext passwords | `security.hash_password` (bcrypt via passlib) |
| NFR-04 | Auth required for protected routes | `deps.get_current_user` (JWT bearer) on every task/dashboard route |
| NFR-05 | Data isolation | `FR-21` above; covered by `tests/test_tasks.py::test_data_isolation_list` etc. |
| NFR-06 | Input validation | Pydantic schemas, 422 on invalid input |
| NFR-07 | Clear error messages | `main.py` custom validation-error handler, per-field messages surfaced in the frontend form |
| NFR-08 | Responsive design | `frontend/src/styles/global.css` (flex/grid layout + mobile breakpoint) |
| NFR-09 | Low-friction task creation | Single-page task form (`TaskFormPage.tsx`) |
| NFR-10 | Data persists across sessions | PostgreSQL with a Docker volume; JWT re-validated from stored token on reload (`AuthContext`) |
| NFR-11 | Error messages on failure | `ApiError` surfaced in every page's error state |
| NFR-12 | Reject invalid create/update | Same validation as NFR-06 |
| NFR-13 | Modular design | Separate `routers/auth.py`, `routers/tasks.py`, `routers/dashboard.py`, `priority.py`, `security.py` |
| NFR-14 | AI-generated code reviewed by a team member | **Action item for the team** — see below |

### Admin additions (not in the official spec)

The admin panel was requested after the spec was written, so it has no FR/NFR
IDs. If you keep the spec as the SDD source of truth, add requirements for it
(e.g. admin role, user management, cross-user task management, platform
analytics) so the SDD narrative stays consistent. Note that it deliberately
sits outside FR-21/NFR-05: those restrict *students* to their own tasks;
admins are a separate, explicitly privileged role.

| Capability | Where implemented | Tests |
|---|---|---|
| Admin role + access control | `deps.require_admin`, `User.is_admin` | `test_students_cannot_use_admin_routes`, `test_registration_never_grants_admin` |
| List / search / view users | `GET /admin/users`, `GET /admin/users/{id}` | `test_admin_lists_all_users_with_task_counts`, `test_admin_user_search_and_role_filter` |
| Create / edit / deactivate / delete users | `POST/PATCH/DELETE /admin/users` | `test_admin_edits_user`, `test_deactivated_user_cannot_log_in_or_use_token`, `test_admin_deletes_user_and_their_tasks` |
| Self-lockout protection | `routers/admin.update_user`, `delete_user` | `test_admin_cannot_demote_or_deactivate_self` |
| View / edit / delete any task | `GET/PATCH/DELETE /admin/tasks` | `test_admin_sees_every_students_tasks`, `test_admin_edits_any_task_and_priority_is_recalculated` |
| Platform analytics | `GET /admin/stats` | `test_admin_stats` |

## For the team: NFR-14 sign-off

This code was AI-generated from `claude/requirements-spec.md`. Per NFR-14, at
least one team member needs to read through it (start with `priority.py`,
`routers/tasks.py`, and `tests/test_priority.py`) and record that review
before it counts as done for the course report.
