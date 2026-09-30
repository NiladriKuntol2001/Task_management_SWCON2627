"""Admin panel API: access control, user management, task management, stats."""
from tests.conftest import future_deadline, past_deadline


def _create_task(client, headers, **overrides):
    payload = {
        "title": "Essay draft",
        "subject": "History",
        "deadline": future_deadline(days=5),
        "difficulty": "Hard",
        "estimated_hours": 5,
    }
    payload.update(overrides)
    resp = client.post("/tasks", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- access control --------------------------------------------------------


def test_registration_never_grants_admin(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Eve", "email": "eve@example.com", "password": "hunter2pass", "is_admin": True},
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["is_admin"] is False


def test_students_cannot_use_admin_routes(client, auth_headers):
    for method, path in [
        ("get", "/admin/stats"),
        ("get", "/admin/users"),
        ("get", "/admin/tasks"),
        ("delete", "/admin/users/some-id"),
        ("delete", "/admin/tasks/some-id"),
    ]:
        resp = getattr(client, method)(path, headers=auth_headers)
        assert resp.status_code == 403, (method, path)


def test_admin_routes_require_login(client):
    assert client.get("/admin/users").status_code == 401


def test_me_reports_admin_flag(client, admin_headers):
    assert client.get("/auth/me", headers=admin_headers).json()["is_admin"] is True


# --- users -------------------------------------------------------------------


def test_admin_lists_all_users_with_task_counts(client, admin_headers, make_user):
    student_headers, student = make_user(email="sam@example.com")
    _create_task(client, student_headers)
    _create_task(client, student_headers, deadline=past_deadline(days=1))

    resp = client.get("/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    rows = {u["email"]: u for u in resp.json()}
    assert set(rows) == {"admin@example.com", "sam@example.com"}
    assert rows["sam@example.com"]["id"] == student["id"]
    assert rows["sam@example.com"]["total_tasks"] == 2
    assert rows["sam@example.com"]["overdue_tasks"] == 1


def test_admin_user_search_and_role_filter(client, admin_headers, make_user):
    make_user(name="Zahra", email="zahra@example.com")
    make_user(name="Khadija", email="khadija@example.com")

    resp = client.get("/admin/users", params={"search": "zah"}, headers=admin_headers)
    assert [u["email"] for u in resp.json()] == ["zahra@example.com"]

    resp = client.get("/admin/users", params={"role": "student"}, headers=admin_headers)
    assert {u["email"] for u in resp.json()} == {"zahra@example.com", "khadija@example.com"}


def test_admin_views_user_detail_with_tasks(client, admin_headers, make_user):
    student_headers, student = make_user(email="sam@example.com")
    _create_task(client, student_headers, title="Lab report")

    resp = client.get(f"/admin/users/{student['id']}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "sam@example.com"
    assert [t["title"] for t in body["tasks"]] == ["Lab report"]
    assert body["tasks"][0]["owner_email"] == "sam@example.com"


def test_admin_edits_user(client, admin_headers, make_user):
    _, student = make_user(email="sam@example.com")
    resp = client.patch(
        f"/admin/users/{student['id']}",
        json={"name": "Samuel", "email": "samuel@example.com"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Samuel"
    assert resp.json()["email"] == "samuel@example.com"


def test_admin_edit_rejects_duplicate_email(client, admin_headers, make_user):
    make_user(email="taken@example.com")
    _, student = make_user(email="sam@example.com")
    resp = client.patch(
        f"/admin/users/{student['id']}", json={"email": "taken@example.com"}, headers=admin_headers
    )
    assert resp.status_code == 409


def test_admin_password_reset_lets_user_log_in_with_new_password(client, admin_headers, make_user):
    _, student = make_user(email="sam@example.com", password="oldpassword1")
    resp = client.patch(
        f"/admin/users/{student['id']}", json={"password": "newpassword1"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert client.post("/auth/login", json={"email": "sam@example.com", "password": "oldpassword1"}).status_code == 401
    assert client.post("/auth/login", json={"email": "sam@example.com", "password": "newpassword1"}).status_code == 200


def test_deactivated_user_cannot_log_in_or_use_token(client, admin_headers, make_user):
    student_headers, student = make_user(email="sam@example.com", password="hunter2pass")
    client.patch(f"/admin/users/{student['id']}", json={"is_active": False}, headers=admin_headers)

    login = client.post("/auth/login", json={"email": "sam@example.com", "password": "hunter2pass"})
    assert login.status_code == 403
    assert client.get("/tasks", headers=student_headers).status_code == 403


def test_admin_can_promote_student(client, admin_headers, make_user):
    student_headers, student = make_user(email="sam@example.com")
    client.patch(f"/admin/users/{student['id']}", json={"is_admin": True}, headers=admin_headers)
    assert client.get("/admin/stats", headers=student_headers).status_code == 200


def test_admin_cannot_demote_or_deactivate_self(client, make_admin):
    headers, admin = make_admin()
    assert client.patch(f"/admin/users/{admin['id']}", json={"is_admin": False}, headers=headers).status_code == 400
    assert client.patch(f"/admin/users/{admin['id']}", json={"is_active": False}, headers=headers).status_code == 400
    assert client.delete(f"/admin/users/{admin['id']}", headers=headers).status_code == 400


def test_admin_can_demote_another_admin_when_one_remains(client, make_admin):
    headers, _ = make_admin()
    _, other = make_admin(email="admin2@example.com")
    resp = client.patch(f"/admin/users/{other['id']}", json={"is_admin": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False


def test_admin_deletes_user_and_their_tasks(client, admin_headers, make_user):
    student_headers, student = make_user(email="sam@example.com")
    task = _create_task(client, student_headers)

    assert client.delete(f"/admin/users/{student['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/admin/users/{student['id']}", headers=admin_headers).status_code == 404
    assert client.patch(f"/admin/tasks/{task['id']}", json={"title": "x"}, headers=admin_headers).status_code == 404


def test_admin_creates_user(client, admin_headers):
    resp = client.post(
        "/admin/users",
        json={"name": "New Student", "email": "new@example.com", "password": "welcome123"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["is_admin"] is False
    assert client.post("/auth/login", json={"email": "new@example.com", "password": "welcome123"}).status_code == 200


# --- tasks -------------------------------------------------------------------


def test_admin_sees_every_students_tasks(client, admin_headers, make_user):
    a_headers, _ = make_user(email="a@example.com")
    b_headers, _ = make_user(email="b@example.com")
    _create_task(client, a_headers, title="A's task")
    _create_task(client, b_headers, title="B's task")

    resp = client.get("/admin/tasks", headers=admin_headers)
    body = resp.json()
    assert body["total"] == 2
    assert {t["owner_email"] for t in body["items"]} == {"a@example.com", "b@example.com"}


def test_admin_task_filters(client, admin_headers, make_user):
    headers, student = make_user(email="a@example.com")
    _create_task(client, headers, title="Late one", subject="Math", deadline=past_deadline(days=2))
    _create_task(client, headers, title="Chill one", subject="Art", difficulty="Easy", estimated_hours=1,
                 deadline=future_deadline(days=30))

    by_search = client.get("/admin/tasks", params={"search": "late"}, headers=admin_headers).json()
    assert [t["title"] for t in by_search["items"]] == ["Late one"]

    overdue = client.get("/admin/tasks", params={"overdue_only": True}, headers=admin_headers).json()
    assert [t["title"] for t in overdue["items"]] == ["Late one"]

    low = client.get("/admin/tasks", params={"priority_level": "Low"}, headers=admin_headers).json()
    assert [t["title"] for t in low["items"]] == ["Chill one"]

    owner = client.get("/admin/tasks", params={"owner_id": student["id"]}, headers=admin_headers).json()
    assert owner["total"] == 2


def test_admin_task_pagination(client, admin_headers, make_user):
    headers, _ = make_user(email="a@example.com")
    for i in range(5):
        _create_task(client, headers, title=f"T{i}")
    page = client.get("/admin/tasks", params={"limit": 2, "offset": 2}, headers=admin_headers).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2


def test_admin_edits_any_task_and_priority_is_recalculated(client, admin_headers, make_user):
    headers, _ = make_user(email="a@example.com")
    task = _create_task(client, headers, difficulty="Easy", estimated_hours=1)  # 33 -> Low
    resp = client.patch(
        f"/admin/tasks/{task['id']}",
        json={"difficulty": "Very Hard", "estimated_hours": 10},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["priority_score"] == 75
    assert resp.json()["priority_level"] == "High"

    # The student sees the admin's change.
    assert client.get(f"/tasks/{task['id']}", headers=headers).json()["difficulty"] == "Very Hard"


def test_admin_marks_task_complete_sets_completed_at(client, admin_headers, make_user):
    headers, _ = make_user(email="a@example.com")
    task = _create_task(client, headers)
    body = client.patch(f"/admin/tasks/{task['id']}", json={"completed": True}, headers=admin_headers).json()
    assert body["completed"] is True
    assert body["completed_at"] is not None

    body = client.patch(f"/admin/tasks/{task['id']}", json={"completed": False}, headers=admin_headers).json()
    assert body["completed_at"] is None


def test_admin_deletes_any_task(client, admin_headers, make_user):
    headers, _ = make_user(email="a@example.com")
    task = _create_task(client, headers)
    assert client.delete(f"/admin/tasks/{task['id']}", headers=admin_headers).status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=headers).status_code == 404


def test_admin_task_edit_validates_input(client, admin_headers, make_user):
    headers, _ = make_user(email="a@example.com")
    task = _create_task(client, headers)
    resp = client.patch(f"/admin/tasks/{task['id']}", json={"estimated_hours": 0}, headers=admin_headers)
    assert resp.status_code == 422


# --- stats -------------------------------------------------------------------


def test_admin_stats(client, admin_headers, make_user):
    a_headers, _ = make_user(email="a@example.com")
    b_headers, _ = make_user(email="b@example.com")
    _create_task(client, a_headers, subject="Math", deadline=past_deadline(days=1))  # overdue
    done = _create_task(client, a_headers, subject="Math")
    client.post(f"/tasks/{done['id']}/complete", headers=a_headers)
    _create_task(client, b_headers, subject="Physics", difficulty="Very Hard", estimated_hours=10,
                 deadline=future_deadline(hours=5))  # 100 -> Critical

    stats = client.get("/admin/stats", headers=admin_headers).json()
    assert stats["users_total"] == 3
    assert stats["students_total"] == 2
    assert stats["admins_total"] == 1
    assert stats["tasks_total"] == 3
    assert stats["tasks_open"] == 2
    assert stats["tasks_completed"] == 1
    assert stats["tasks_overdue"] == 1
    assert stats["critical_open"] >= 1
    assert stats["completion_rate"] == 33.3
    assert stats["students_with_overdue"] == 1

    bands = {b["label"]: b["count"] for b in stats["deadline_pressure"]}
    assert bands["Overdue"] == 1 and bands["< 24 hours"] == 1

    subjects = {s["subject"]: s for s in stats["subjects"]}
    assert subjects["Math"]["completed"] == 1 and subjects["Math"]["overdue"] == 1

    assert len(stats["daily_activity"]) == 14
    assert stats["daily_activity"][-1]["created"] == 3
    assert stats["daily_activity"][-1]["completed"] == 1

    assert stats["students_at_risk"][0]["email"] == "a@example.com"
    assert len(stats["recent_tasks"]) == 3


def test_stale_priority_is_refreshed_on_read(client, auth_headers):
    """A task created 20 days out is Low; if its deadline moves close (simulated by
    editing the stored deadline directly in the DB), reads recompute it."""
    from datetime import datetime, timedelta, timezone

    from app.models import Task
    from tests.conftest import TestingSessionLocal

    task = _create_task(client, auth_headers, difficulty="Very Hard", estimated_hours=10,
                        deadline=future_deadline(days=20))
    # 10*0.5 + 100*0.3 + 100*0.2 = 55 -> Medium
    assert task["priority_level"] == "Medium"

    db = TestingSessionLocal()
    db.query(Task).filter(Task.id == task["id"]).update(
        {"deadline": datetime.now(timezone.utc) + timedelta(hours=3)}
    )
    db.commit()
    db.close()

    fresh = client.get(f"/tasks/{task['id']}", headers=auth_headers).json()
    assert fresh["priority_score"] == 100
    assert fresh["priority_level"] == "Critical"
