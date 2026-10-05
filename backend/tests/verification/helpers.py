"""Shared helpers for the independent verification suite (Member 3)."""
from tests.conftest import future_deadline, past_deadline  # noqa: F401


def make_task(client, headers, title="Task", subject="Math", deadline=None,
              difficulty="Medium", hours=5, **extra):
    """POST /tasks with sensible defaults (4 days, Medium, 5 h -> score 50)."""
    body = {
        "title": title,
        "subject": subject,
        "deadline": deadline or future_deadline(days=4),
        "difficulty": difficulty,
        "estimated_hours": hours,
        **extra,
    }
    return client.post("/tasks", json=body, headers=headers)
