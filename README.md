# Smart Student Task Manager

A web app where students manage assignments, exams, and projects. The system
scores each task's priority from its deadline, difficulty, and estimated time,
classifies it (Low/Medium/High/Critical), and recommends what to work on next.

Built to the exact spec in `claude/requirements-spec.md` (FR-01 through FR-21,
NFR-01 through NFR-14, and the fixed priority formula in Section 3).

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
    deps.py             Auth dependency (get_current_user)
    routers/
      auth.py           /auth: register, login, logout, me
      tasks.py          /tasks: CRUD, filter, sort, upcoming, complete
      dashboard.py      /dashboard: summary + recommendation
  alembic/               DB migrations
  tests/                 pytest suite (auth, tasks, priority, dashboard)
frontend/
  src/
    api/client.ts        Typed fetch client
    context/AuthContext.tsx
    pages/                Login, Register, Dashboard, Tasks, Task form/detail
    components/           Navbar, TaskCard, PriorityBadge, ProtectedRoute
docker-compose.yml
```

## Running it

### Option A — Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env      # edit SECRET_KEY for anything beyond local use
docker compose up --build
```

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

> **Note on this build:** the sandbox this project was generated in has no
> outbound access to PyPI or the npm registry, so `pip install` / `npm install`
> and the resulting `pytest` / `npm run build` could not be executed here to
> confirm a green run. The code was written and reviewed carefully against the
> spec (see the traceability table below and the inline `FR-xx`/`NFR-xx`
> comments throughout `backend/app/`), but please run `pytest` and
> `npm run build` yourselves as the first step after cloning — that's also
> the human-review step NFR-14 asks for.

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

## For the team: NFR-14 sign-off

This code was AI-generated from `claude/requirements-spec.md`. Per NFR-14, at
least one team member needs to read through it (start with `priority.py`,
`routers/tasks.py`, and `tests/test_priority.py`) and record that review
before it counts as done for the course report.
