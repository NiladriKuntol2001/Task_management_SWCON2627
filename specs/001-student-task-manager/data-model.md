# Data Model: Smart Student Task Manager

## Entities

### User

Represents a person with access to the application. Each user has a unique identifier and a role that determines which features are available.

**Fields**
- user_id: unique account identifier
- name: display name
- email: unique login/contact address
- password_hash: secure credential representation
- role: student or admin
- is_active: whether the account can log in
- created_at: account registration time

**Rules**
- email must be unique across active accounts
- admin-only actions require elevated authorization
- self-service profile changes must verify identity

### Task

Represents a student’s assignment, project, or exam-related work item.

**Fields**
- task_id: unique task identifier
- owner_id: user who created and owns the task
- title: short summary of the work item
- subject: course or work category
- deadline: due date/time
- difficulty: difficulty value used in scoring
- hours: effort estimate
- status: open, completed, or otherwise active state
- completed_at: completion timestamp when applicable
- priority_score: derived score used for sorting and recommendations
- created_at: task creation time

**Rules**
- task fields must be present and valid before persistence
- priority impacts ordering and must be recalculated when deadlines, difficulty, or hours change
- only owners or authorized admins may view or modify a task

### Priority Score

A derived, non-user-authored value used to compare the urgency and workload of tasks.

**Derived from**
- deadline urgency
- difficulty rating
- effort estimate

**Behavior**
- recalculated whenever relevant task inputs change
- used for user rankings, dashboard recommendations, and overdue detection

### Admin Overview

A read-only aggregate view used by administrators to understand platform activity without exposing unrelated personal data.

**Data covered**
- totals by student and task state
- overdue and critical workload metrics
- recent activity and completion trends
- user-level management information and filtering options

## Relationships

- One user may own many tasks.
- Each task belongs to exactly one owner.
- Admins may view aggregate data but do not replace user ownership.
- Priority score is derived from task metadata rather than stored independently as a user-managed field.
