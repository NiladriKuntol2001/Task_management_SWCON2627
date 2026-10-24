# Smart Student Task Manager Constitution


Version change: 0.0.0 (template placeholder) → 1.0.0
Modified principles: none (template placeholders replaced with project-specific governance)
Added sections: Quality Standards; Delivery Workflow
Removed sections: none

- 2026-11-01: confirm the original adoption date before final ratification.


## Core Principles

### I. Student-First Value Delivery
Every feature MUST directly support a student’s ability to plan, prioritize, and complete assignments, projects, and exams with clear deadlines and actionable next steps. The product MUST NOT add workflow friction, obscure the primary task-management flow, or create unnecessary administrative overhead that reduces clarity and accountability.

### II. Task Integrity and Accurate Priority
Every task record MUST contain valid required fields, and the deadline, difficulty, and effort estimates MUST remain consistent before a task is saved. Priority calculation and task classification MUST be derived from the approved formula and recalculated whenever inputs change, so user-facing ordering, dashboards, and recommendations reflect current reality instead of stale values.

### III. Test-First Validation
No change to the product may ship without a failing or missing test that captures the behavior being fixed or added. The team MUST validate the real API and business logic paths in automated tests before declaring a feature complete, and any regression MUST be corrected before merge.

### IV. Security, Access Control, and Data Privacy
Authentication and authorization are mandatory for every protected surface. User data MUST remain isolated by account, admin-only capabilities MUST be restricted to authorized roles, and password or session handling MUST never be weakened to increase convenience. Sensitive changes such as email or password updates require explicit verification and must be enforced at both the UI and server boundary.

### V. Operational Clarity and Change Control
The codebase MUST remain understandable, reviewable, and deployable from a documented workflow. Changes that modify schema, business rules, or user permissions require clear migration notes, traceability to requirements, and a deliberate review of downstream impact before release.

## Quality Standards
All releases MUST keep the backend and frontend aligned with the functional and non-functional requirements in the product backlog. The team MUST preserve priority logic, user isolation guarantees, and admin safeguards as first-class requirements, not optional enhancements. A release is not acceptable when a regression causes task ordering, access control, or data integrity to drift from the specification.

## Delivery Workflow
Development work MUST follow a disciplined sequence: define the requirement, write or update the failing validation, implement the minimal change, verify the affected behavior, and review the diff for security, data integrity, and UX impact. Migrations and configuration changes MUST be explicit and reversible where possible, and any change that affects existing users or stored data requires a clear migration path and review before deployment.

## Governance
This Constitution supersedes informal practices and unreviewed shortcuts. Any proposal that changes product requirements, data model constraints, access rules, or release criteria MUST be documented, reviewed, and approved before implementation proceeds.

Amendments MUST:
- state the reason for the change and the affected principle or workflow section;
- identify the scope of impact on product behavior, data model, testing, or security;
- include the new version number following semantic versioning;
- be reviewed for compliance with the project’s functional and non-functional requirements before approval.

Versioning policy:
- MAJOR changes remove or redefine a non-negotiable governance rule or a core product principle;
- MINOR changes add a new principle or materially expand required behavior;
- PATCH changes clarify language, correct errors, or refine wording without changing required outcomes.

Compliance review expectations:
- All merged changes MUST be traceable to requirements, tests, or documented design rationale.
- Each release MUST confirm that task priority logic, authentication, and access boundaries remain consistent with this Constitution.
- Any unresolved exception or temporary waiver MUST be recorded in the project record and assigned a follow-up owner and deadline.

**Version**: 1.0.0 | **Ratified**: 2026-11-01 | **Last Amended**: 2026-10-24
