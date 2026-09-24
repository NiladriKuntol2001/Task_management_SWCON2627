"""Task CRUD, validation, filtering, sorting, data isolation (FR-04..FR-18, FR-21)."""
from tests.conftest import future_deadline, past_deadline


def _create_task(client, headers, **overrides):
    payload = {
        "title": "Finish calculus homework",
        "subject": "Math",
        "deadline": future_deadline(days=5),
        "difficulty": "Hard",
        "estimated_hours": 5,
    }
    payload.update(overrides)
    return client.post("/tasks", json=payload, headers=headers)


def test_create_task_computes_priority(client, auth_headers):
    resp = _create_task(client, auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["priority_score"] == 59  # from test_priority.py: 5d/Hard/5h -> 59
    assert body["priority_level"] == "Medium"
    assert body["completed"] is False


def test_create_task_validation_errors(client, auth_headers):
    # empty title
    resp = _create_task(client, auth_headers, title="")
    assert resp.status_code == 422

    # non-positive estimated hours
    resp = _create_task(client, auth_headers, estimated_hours=0)
    assert resp.status_code == 422

    # invalid difficulty
    resp = _create_task(client, auth_headers, difficulty="Impossible")
    assert resp.status_code == 422

    # missing/invalid deadline
    resp = _create_task(client, auth_headers, deadline="not-a-date")
    assert resp.status_code == 422


def test_get_task_details(client, auth_headers):
    created = _create_task(client, auth_headers).json()
    resp = client.get(f"/tasks/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Finish calculus homework"


def test_edit_task_recalculates_priority(client, auth_headers):
    created = _create_task(client, auth_headers, difficulty="Easy", estimated_hours=1).json()
    # deadline in 5 days -> 50, Easy -> 20, 1 hour -> 10: 50*0.5+20*0.3+10*0.2=33 -> Low
    assert created["priority_score"] == 33
    assert created["priority_level"] == "Low"

    resp = client.patch(
        f"/tasks/{created['id']}",
        json={"difficulty": "Very Hard", "estimated_hours": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    # deadline unchanged (5 days -> 50), difficulty Very Hard -> 100, hours 10 -> 100
    # 50*0.5 + 100*0.3 + 100*0.2 = 25+30+20 = 75
    assert updated["priority_score"] == 75
    assert updated["priority_level"] == "High"


def test_edit_only_own_task(client, auth_headers, make_user):
    created = _create_task(client, auth_headers).json()
    other_headers, _ = make_user(email="mallory@example.com")

    resp = client.patch(
        f"/tasks/{created['id']}", json={"title": "Hacked"}, headers=other_headers
    )
    assert resp.status_code == 404


def test_mark_complete(client, auth_headers):
    created = _create_task(client, auth_headers).json()
    resp = client.post(f"/tasks/{created['id']}/complete", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["completed"] is True


def test_delete_task(client, auth_headers):
    created = _create_task(client, auth_headers).json()
    resp = client.delete(f"/tasks/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f"/tasks/{created['id']}", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_only_own_task(client, auth_headers, make_user):
    created = _create_task(client, auth_headers).json()
    other_headers, _ = make_user(email="mallory2@example.com")

    resp = client.delete(f"/tasks/{created['id']}", headers=other_headers)
    assert resp.status_code == 404


def test_filter_by_subject_and_completion(client, auth_headers):
    _create_task(client, auth_headers, title="Math HW", subject="Math")
    physics = _create_task(client, auth_headers, title="Physics Lab", subject="Physics").json()
    client.post(f"/tasks/{physics['id']}/complete", headers=auth_headers)

    resp = client.get("/tasks", params={"subject": "Math"}, headers=auth_headers)
    assert {t["subject"] for t in resp.json()} == {"Math"}

    resp = client.get("/tasks", params={"completed": True}, headers=auth_headers)
    titles = {t["title"] for t in resp.json()}
    assert titles == {"Physics Lab"}

    resp = client.get("/tasks", params={"completed": False}, headers=auth_headers)
    titles = {t["title"] for t in resp.json()}
    assert titles == {"Math HW"}


def test_sort_by_priority_with_deadline_tiebreak(client, auth_headers):
    # Two tasks tied on priority score, different deadlines -> earlier deadline first (FR-14)
    t1 = _create_task(
        client, auth_headers, title="A", deadline=future_deadline(days=10, hours=1)
    ).json()
    t2 = _create_task(
        client, auth_headers, title="B", deadline=future_deadline(days=9)
    ).json()
    assert t1["priority_score"] == t2["priority_score"]  # both in 7-14 day band

    resp = client.get("/tasks", params={"sort_by": "priority"}, headers=auth_headers)
    ordered_titles = [t["title"] for t in resp.json()]
    assert ordered_titles.index("B") < ordered_titles.index("A")


def test_sort_by_deadline(client, auth_headers):
    _create_task(client, auth_headers, title="Later", deadline=future_deadline(days=10))
    _create_task(client, auth_headers, title="Sooner", deadline=future_deadline(days=1))

    resp = client.get("/tasks", params={"sort_by": "deadline"}, headers=auth_headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Sooner", "Later"]


def test_overdue_detection(client, auth_headers):
    overdue = _create_task(
        client, auth_headers, title="Late", deadline=past_deadline(days=2)
    ).json()
    assert overdue["is_overdue"] is True

    resp = client.get("/tasks", params={"overdue_only": True}, headers=auth_headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Late"]


def test_completed_task_is_not_overdue(client, auth_headers):
    task = _create_task(
        client, auth_headers, title="Late but done", deadline=past_deadline(days=2)
    ).json()
    client.post(f"/tasks/{task['id']}/complete", headers=auth_headers)

    resp = client.get(f"/tasks/{task['id']}", headers=auth_headers)
    assert resp.json()["is_overdue"] is False


def test_upcoming_deadlines_view(client, auth_headers):
    _create_task(client, auth_headers, title="Soon", deadline=future_deadline(days=3))
    _create_task(client, auth_headers, title="Far", deadline=future_deadline(days=30))

    resp = client.get("/tasks/upcoming", params={"days": 7}, headers=auth_headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Soon"]


def test_data_isolation_list(client, auth_headers, make_user):
    _create_task(client, auth_headers, title="Mine")
    other_headers, _ = make_user(email="trent@example.com")
    _create_task(client, other_headers, title="Theirs")

    resp = client.get("/tasks", headers=auth_headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Mine"]

    resp = client.get("/tasks", headers=other_headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Theirs"]
