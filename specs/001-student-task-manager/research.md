# Research: Smart Student Task Manager

## Decision Summary

The project will continue with the existing architecture: a FastAPI backend and React frontend operating against a PostgreSQL-backed data model with SQLite-backed tests. This preserves the working student task workflow and avoids reworking the app around a different stack or persistence approach.

## Findings

### 1. Core user value
The product is centered on helping students manage coursework with deadlines, effort estimates, and priority recommendations. The central business rule is that urgency should be visible and actionable, not hidden behind manual sorting.

### 2. Priority logic is a first-class domain rule
The priority formula and classification are not optional UI enhancements. They define the ordering and recommendation behavior that students rely on, so the backend must remain the authoritative source for recalculation and validation.

### 3. Access isolation is mandatory
Every task and profile action must be scoped to the current user unless the caller is explicitly authorized as an admin. This requirement affects authentication, service methods, route guards, and any data reads that populate dashboard summaries.

### 4. Admin capabilities are a separate role, not a special case of the user flow
The admin experience should present aggregate information and user/task management tools without exposing personal records outside the authorized scope. This is best implemented as a strict role boundary at the API layer and mirrored in the UI.

### 5. Validation strategy should be behavior-first
The most meaningful checks are route-level and user-flow validation: account creation/login, task creation and completion, dashboard sorting, and role-based access control. These are the behaviors that directly prove the feature works.

## Resolved Clarifications

- No unresolved NEEDS CLARIFICATION markers remain in the feature specification.
- Existing project conventions already define the relevant stack, data rules, and operational constraints.
