# Quickstart Validation Guide

## Prerequisites

- Docker and Docker Compose available on the local machine
- Python 3.12 for backend checks
- Node.js and npm for frontend validation

## Validate with Docker

1. Start the stack from the repository root:
   `docker compose up --build`
2. Confirm the frontend is reachable at `http://localhost:3000`.
3. Confirm the API is reachable at `http://localhost:8000/docs`.
4. Verify a student can create an account, create a task, and view a prioritized list.
5. Verify an admin can access the admin pages and review aggregate activity without breaching user isolation.

## Validate backend behavior

1. Change to the backend directory:
   `cd backend`
2. Run the backend test suite:
   `pytest`
3. Confirm priority, authentication, profile, task, and admin tests pass.

## Validate front-end health

1. Change to the frontend directory:
   `cd frontend`
2. Install dependencies if needed:
   `npm install`
3. Run a production build check:
   `npm run build`
4. Confirm the build succeeds and the application initializes without route or bundle errors.

## Expected outcomes

- Students can create and manage their own tasks.
- The dashboard highlights deadlines, overdue work, and recommended next actions.
- The priority score updates accurately when inputs change.
- Admin pages are available only to authorized users.
- Data is isolated by account and protected from unauthorized access.
