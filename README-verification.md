# Verification suite (Member 3)

Copy these into the repository root (same folder names) and commit them.

| Path | Purpose |
| --- | --- |
| `backend/tests/verification/` | Independent tests written from the specification (not from the code) |
| `.github/workflows/ci.yml` | Runs all tests, coverage (>= 80%), bandit, pip-audit and the frontend build on every pull request |
| `.github/ISSUE_TEMPLATE/defect_report.md` | Defect log template (GitHub Issues) |
| `.github/pull_request_template.md` | Records who reviewed AI-generated code (NFR-14) |
| `fixes/DEF-01-DEF-02-schemas.patch` | Candidate fix for the two defects, verified locally (apply with `git apply`) |

Run locally:

    cd backend
    pip install -r requirements.txt pytest-cov
    pytest                          # everything
    pytest tests/verification       # only the independent suite
    pytest -k TC_PRI                # one test area (TC_AUTH, TC_TASK, TC_PRI, TC_SEC ...)
    pytest --runxfail               # show the two known defects as failures

The two tests marked `xfail(strict=True)` record known defects (DEF-01, DEF-02).
After the fix is merged they start passing, strict mode then fails the build,
and the marker must be deleted.
