"""Dashboard summary and 'what should I work on today' recommendation (FR-19, FR-20)."""
from tests.conftest import future_deadline, past_deadline


def _create_task(client, headers, **overrides):
    payload = {
        "title": "Task",
        "subject": "Math",
        "deadline": future_deadline(days=5),
        "difficulty": "Hard",
        "estimated_hours": 5,
    }
    payload.update(overrides)
    return client.post("/tasks", json=payload, headers=headers).json()


def test_dashboard_counts(client, auth_headers):
    _create_task(client, auth_headers, title="Incomplete high", difficulty="Very Hard", estimated_hours=10)
    done = _create_task(client, auth_headers, title="Done")
    client.post(f"/tasks/{done['id']}/complete", headers=auth_headers)
    _create_task(client, auth_headers, title="Overdue", deadline=past_deadline(days=1))

    resp = client.get("/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["incomplete_count"] == 2
    assert body["completed_count"] == 1
    assert body["overdue_count"] == 1
    assert body["high_priority_count"] >= 1


def test_dashboard_recommends_highest_priority_incomplete_task(client, auth_headers):
    _create_task(client, auth_headers, title="Low priority", difficulty="Easy", estimated_hours=1, deadline=future_deadline(days=30))
    critical = _create_task(
        client,
        auth_headers,
        title="Critical one",
        difficulty="Very Hard",
        estimated_hours=10,
        deadline=past_deadline(hours=1),
    )

    resp = client.get("/dashboard", headers=auth_headers)
    assert resp.json()["recommended_task"]["id"] == critical["id"]


def test_dashboard_recommendation_ignores_completed_tasks(client, auth_headers):
    critical = _create_task(
        client,
        auth_headers,
        title="Critical but done",
        difficulty="Very Hard",
        estimated_hours=10,
        deadline=past_deadline(hours=1),
    )
    client.post(f"/tasks/{critical['id']}/complete", headers=auth_headers)
    remaining = _create_task(client, auth_headers, title="Only incomplete left")

    resp = client.get("/dashboard", headers=auth_headers)
    assert resp.json()["recommended_task"]["id"] == remaining["id"]


def test_dashboard_no_recommendation_when_no_incomplete_tasks(client, auth_headers):
    resp = client.get("/dashboard", headers=auth_headers)
    assert resp.json()["recommended_task"] is None


def test_dashboard_is_scoped_to_current_user(client, auth_headers, make_user):
    _create_task(client, auth_headers, title="Mine")
    other_headers, _ = make_user(email="oscar@example.com")
    _create_task(client, other_headers, title="Theirs")
    _create_task(client, other_headers, title="Theirs2")

    resp = client.get("/dashboard", headers=auth_headers)
    assert resp.json()["incomplete_count"] == 1
