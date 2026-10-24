# API Contract: Smart Student Task Manager

## Overview

The application exposes a web API for user authentication, task management, dashboard insights, profile updates, and admin operations. All protected operations enforce user ownership and role-based access.

## Authentication

### POST /auth/register
- Creates a new student account
- Request body includes identifying fields and secure credentials
- Response: created user summary or validation error

### POST /auth/login
- Authenticates a user
- Response: session token or access credentials

### POST /auth/logout
- Invalidates the current session token

## Task Lifecycle

### GET /tasks
- Returns the current user’s tasks with filtering and sorting options
- Supports subject and completion filtering

### POST /tasks
- Creates a new task for the authenticated user
- Validates required fields before persistence

### GET /tasks/{id}
- Returns details for one owned task

### PATCH /tasks/{id}
- Updates owned task fields, including priority-sensitive values

### DELETE /tasks/{id}
- Removes a task owned by the current user

### POST /tasks/{id}/complete
- Marks a task complete and updates completion metadata

## Dashboard and Personal Insights

### GET /dashboard
- Returns the user’s workload overview, overdue items, upcoming tasks, and recommended next action

### GET /tasks/upcoming
- Returns tasks due soon for the authenticated user

## Profile Management

### GET /profile
- Returns the authenticated user’s profile information

### PATCH /profile/email
- Updates the authenticated user’s email with validation

### PATCH /profile/password
- Updates the authenticated user’s password with verification checks

## Admin Operations

### GET /admin
- Returns aggregate platform metrics and summary data

### GET /admin/users
- Lists users with filters and role information

### GET /admin/users/{id}
- Shows user details and their tasks within scope

### PATCH /admin/users/{id}
- Updates account properties in a controlled admin flow

### DELETE /admin/users/{id}
- Removes a user only when allowed by policy

## Security Contracts

- Non-admin callers must receive an authorization failure when accessing admin routes.
- A user may only view or modify their own task data unless they are authorized as an admin.
- Sensitive updates require verification and must reject invalid or duplicate values.
- The server must reject malformed input before persisting changes.
