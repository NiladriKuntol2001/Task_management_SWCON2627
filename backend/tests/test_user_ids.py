"""Unique numeric user IDs, and the main administrator fixed at ID 1."""
from app.models import ROOT_ADMIN_ID


def test_main_admin_is_user_1_with_required_credentials(client):
    resp = client.post("/auth/login", json={"email": "admin123@gmail.com", "password": "admin@123"})
    assert resp.status_code == 200
    user = resp.json()["user"]
    assert user["id"] == ROOT_ADMIN_ID == 1
    assert user["email"] == "admin123@gmail.com"
    assert user["is_admin"] is True


def test_students_get_unique_sequential_ids_after_admin(make_user):
    ids = [make_user(email=f"s{i}@example.com")[1]["id"] for i in range(3)]
    assert ids == [2, 3, 4]
    assert all(isinstance(i, int) for i in ids)


def test_ids_are_not_reused_after_delete(client, admin_headers, make_user):
    _, first = make_user(email="first@example.com")
    _, second = make_user(email="second@example.com")
    assert client.delete(f"/admin/users/{second['id']}", headers=admin_headers).status_code == 204
    _, third = make_user(email="third@example.com")
    assert third["id"] > second["id"] > first["id"]


def test_seeding_twice_keeps_admin_at_1_and_keeps_changed_password(client, admin_headers):
    from app.seed import ensure_root_admin
    from tests.conftest import TestingSessionLocal

    client.put(
        "/profile/password",
        json={"current_password": "admin@123", "new_password": "newadminpass1", "confirm_new_password": "newadminpass1"},
        headers=admin_headers,
    )
    db = TestingSessionLocal()
    root = ensure_root_admin(db, "admin123@gmail.com", "admin@123")  # simulates an app restart
    assert root.id == 1
    db.close()
    assert client.post("/auth/login", json={"email": "admin123@gmail.com", "password": "newadminpass1"}).status_code == 200


def test_task_owner_id_is_numeric(client, make_user):
    headers, user = make_user(email="sam@example.com")
    task = client.post(
        "/tasks",
        json={"title": "T", "subject": "S", "deadline": "2030-01-01T00:00:00Z", "difficulty": "Easy", "estimated_hours": 1},
        headers=headers,
    ).json()
    assert task["owner_id"] == user["id"]


def test_admin_can_search_users_by_id(client, admin_headers, make_user):
    make_user(name="Zahra", email="zahra@example.com")  # id 2
    _, k = make_user(name="Khadija", email="khadija@example.com")  # id 3
    rows = client.get("/admin/users", params={"search": str(k["id"])}, headers=admin_headers).json()
    assert [u["email"] for u in rows] == ["khadija@example.com"]
    rows = client.get("/admin/users", params={"search": "#1"}, headers=admin_headers).json()
    assert [u["id"] for u in rows] == [1]


def test_tokens_with_non_numeric_subject_are_rejected(client):
    from app.security import create_access_token

    token = create_access_token("3f0c2a1e-uuid-style-subject")
    assert client.get("/profile", headers={"Authorization": f"Bearer {token}"}).status_code == 401


# --- main admin protections (enforced even against other admins) -------------


def test_other_admin_cannot_modify_or_delete_main_admin(client, make_admin):
    headers, _ = make_admin(email="second-admin@example.com")
    assert client.patch("/admin/users/1", json={"email": "x@example.com"}, headers=headers).status_code == 403
    assert client.patch("/admin/users/1", json={"is_admin": False}, headers=headers).status_code == 403
    assert client.patch("/admin/users/1", json={"is_active": False}, headers=headers).status_code == 403
    assert client.patch("/admin/users/1", json={"password": "takeover123"}, headers=headers).status_code == 403
    assert client.delete("/admin/users/1", headers=headers).status_code == 403
    # Still intact.
    assert client.post("/auth/login", json={"email": "admin123@gmail.com", "password": "admin@123"}).status_code == 200


def test_main_admin_name_can_still_be_edited(client, admin_headers):
    resp = client.patch("/admin/users/1", json={"name": "Head Admin"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Head Admin"
    assert resp.json()["email"] == "admin123@gmail.com"


def test_nobody_can_register_with_main_admin_email(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Imposter", "email": "admin123@gmail.com", "password": "whatever123"},
    )
    assert resp.status_code == 409
