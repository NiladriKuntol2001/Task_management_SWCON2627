# Verification suite (Member 3)

| Path | Purpose |
| --- | --- |
| `backend/tests/verification/` | Independent tests written from the specification (not from the code) |
| `.github/workflows/ci.yml` | Runs all tests, coverage (>= 80%), bandit, pip-audit and the frontend build on every push and pull request |
| `DEF-01-DEF-02-schemas.patch` | Fix for DEF-01 and DEF-02 (now applied; kept for the record) |

Run locally:

    cd backend
    pip install -r requirements.txt pytest-cov
    pytest                          # everything
    pytest tests/verification       # only the independent suite
    pytest -k TC_PRI                # one test area (TC_AUTH, TC_TASK, TC_PRI, TC_SEC ...)

The tests marked `xfail(strict=True)` recorded known defects (DEF-01, DEF-02, DEF-03).
After the fix was merged on 24 October 2026 they started passing, so the markers were
deleted and they now run as normal regression tests.
## Defect status

| ID | Defect | Status |
| --- | --- | --- |
| DEF-01 | `PATCH /tasks/{id}` with an explicit `null` field (e.g. `{"title": null}`) crashed with a 500 instead of returning a 422 | **Fixed**: `TaskUpdate` rejects null fields (`backend/app/schemas.py`) |
| DEF-02 | Email addresses were case-sensitive: `Alice@Example.com` and `alice@example.com` could register as separate accounts, and login depended on letter case | **Fixed**: emails are lowercased on register, login, profile and admin updates (`backend/app/schemas.py`) |
| DEF-03 | Overdue tasks were listed under upcoming deadlines (`/tasks/upcoming`) | **Fixed**: upcoming only returns tasks due between now and the horizon; overdue tasks are reported separately (`backend/app/routers/tasks.py`) |

Re-verified on 2026-10-24: all 288 backend tests pass, and each defect was
re-checked directly against the API.
Re-tested independently on 2026-10-30 (commit 7d6352f): 171 of 171 verification tests
and 289 of 289 backend tests pass.
