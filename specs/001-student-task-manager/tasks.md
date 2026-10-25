# Tasks: Smart Student Task Manager

**Input**: Design documents from `/specs/001-student-task-manager/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by the real MVP scope to reuse existing working functionality and keep the implementation focused on the student task flow.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Phase 1: Setup (MVP Baseline)

**Purpose**: Confirm the repository already contains the intended stack and avoid re-creating working components.

- [X] T001 Confirm the existing FastAPI backend and React frontend are the correct starting point instead of creating a new stack in backend/ and frontend/
- [X] T002 Validate the Docker and local runtime setup in docker-compose.yml, backend/Dockerfile, and frontend/Dockerfile against README.md
- [X] T003 [P] Review environment assumptions in backend/.env.example and frontend/.env.example and confirm the project is ready for local validation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Reuse the existing foundations and verify the core rules that must hold before User Story 1 can be trusted.

- [X] T004 Confirm the shared data model and persistence baseline in backend/app/models.py and backend/alembic/versions/ match the project’s requirements and do not need re-implementation
- [X] T005 Confirm authentication, password hashing, and token handling in backend/app/security.py and backend/app/deps.py remain the source of truth for protected routes
- [X] T006 [P] Confirm request validation rules in backend/app/schemas.py cover required fields, valid difficulty values, positive hours, and valid deadlines
- [X] T007 [P] Confirm the exact priority implementation in backend/app/priority.py follows the approved formula: Deadline Score × 0.50 + Difficulty Score × 0.30 + Time Score × 0.20, with classification bands 80–100 Critical, 60–79 High, 40–59 Medium, 0–39 Low
- [X] T008 Confirm task ownership and admin guard logic in backend/app/task_service.py, backend/app/routers/tasks.py, and backend/app/routers/admin.py are the required foundation for User Story 1

**Checkpoint**: Foundation ready - User Story 1 can begin with no breadth expansion beyond the MVP.

---

## Phase 3: User Story 1 - Manage coursework and priorities (Priority: P1) 🎯 MVP

**Goal**: Deliver the core student workflow: create, view, update, complete, and delete tasks while preserving task ownership and exact priority behavior.

**Independent Test**: A student can create tasks with different deadlines, difficulties, and time estimates, then confirm the system records them correctly, applies the exact priority formula, and keeps each user’s tasks isolated.

### Tests for User Story 1

- [X] T009 [P] [US1] Add or confirm explicit CRUD coverage in backend/tests/test_tasks.py for create, read, update, complete, and delete flows
- [X] T010 [US1] Add or confirm validation tests in backend/tests/test_tasks.py for empty title, invalid deadline, unknown difficulty, and non-positive hours
- [X] T011 [US1] Add or confirm exact priority formula tests in backend/tests/test_priority.py covering all deadline bands, difficulty scores, time caps, and classification thresholds from the approved requirements
- [X] T012 [US1] Add or confirm user-data isolation tests in backend/tests/test_tasks.py proving that one user cannot view or modify another user’s tasks
- [X] T013 [US1] Add or confirm sorting and deadline checks in backend/tests/test_tasks.py for priority ordering, deadline tie-breaks, overdue detection, and upcoming-deadline filtering

### Implementation for User Story 1

- [X] T014 [US1] Reuse the existing task route implementation in backend/app/routers/tasks.py and backend/app/task_service.py without re-creating working logic; only fix gaps identified by failing tests
- [X] T015 [P] [US1] Reuse the current frontend task flow in frontend/src/pages/TasksPage.tsx, frontend/src/pages/TaskFormPage.tsx, frontend/src/pages/TaskDetailPage.tsx, and frontend/src/components/TaskCard.tsx to match the existing API contract rather than redesigning the interface
- [ ] T016 [US1] Final User Story 1 validation: run the focused backend task and priority suites plus the task-related README contract checks before moving beyond the MVP

**Checkpoint**: At this point, the MVP should be independently testable and ready for review without broadening scope to admin or dashboard work.

---

## Phase 4: Final MVP Validation

**Purpose**: Clear final validation order so no extra scope is introduced before the student task workflow is confirmed.

- [X] T017 [P] Review the implementation against README.md, the requirements formula, and the MVP scope to confirm no unrelated admin or second-story features are introduced
- [ ] T018 [P] Run the final backend validation sequence in the correct order: auth checks, task CRUD/validation, priority calculations, and user-data isolation; stop on any failed check before moving forward

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks User Story 1.
- **User Story 1 (Phase 3)**: Depends on Foundational completion and is the only story in scope for the MVP.
- **Final MVP Validation (Phase 4)**: Depends on all User Story 1 tasks being complete.

### Parallel Opportunities

- Setup tasks T001-T003 can run in parallel.
- Foundational tasks T006-T007 can be parallelized once the core auth and schemas are confirmed.
- Story tasks T009-T013 can be executed in parallel when the shared task contracts are already confirmed, but the entire set still depends on the foundation.
- Final validation tasks T017-T018 are post-MVP gates and should run after all story tasks are complete.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate only the CRUD, validation, priority, and isolation behavior before broadening scope
5. Do not advance to admin or dashboard stories during this implementation pass

### Incremental Delivery

1. Reuse existing working code in backend/app and frontend/src.
2. Validate the exact priority rules before changing task logic.
3. Fix only the failures surfaced by task and priority tests.
4. Keep the final gate focused on the MVP and do not add new feature work.

---

## Notes

- Reuse, confirm, and validate existing working functionality before creating replacements.
- The exact priority formula must remain unchanged: Deadline Score × 0.50 + Difficulty Score × 0.30 + Time Score × 0.20.
- The explicit test coverage required for the MVP is: CRUD, validation, priority calculations, and user-data isolation.
- This task list intentionally excludes User Stories 2 and 3 so the project stays within the approved MVP and avoids unneeded scope expansion.
- T016 and T018 remain unchecked because pytest could not be run: the available Python is 3.13, while the project specifies 3.12, and the pinned psycopg2-binary 2.9.9 dependency failed to build without Microsoft Visual C++ 14.0. Docker and Node.js are also unavailable for runtime/build checks.
