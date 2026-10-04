"""Profile: view account, change email, change password (new != previous)."""


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_profile_shows_numeric_user_id(client, make_user):
    headers, user = make_user(email="sam@example.com")
    body = client.get("/profile", headers=headers).json()
    assert body["id"] == user["id"]
    assert isinstance(body["id"], int)
    assert body["email"] == "sam@example.com"
    assert "hashed_password" not in body


def test_profile_requires_login(client):
    assert client.get("/profile").status_code == 401
    assert client.put("/profile/email", json={"new_email": "x@example.com", "current_password": "x"}).status_code == 401
    assert client.put(
        "/profile/password",
        json={"current_password": "x", "new_password": "newpassword1", "confirm_new_password": "newpassword1"},
    ).status_code == 401


# --- email -------------------------------------------------------------------


def test_change_email(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = client.put(
        "/profile/email",
        json={"new_email": "samuel@example.com", "current_password": "hunter2pass"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "samuel@example.com"

    # Old email no longer logs in; new one does, with the same password. Token stays valid.
    assert _login(client, "sam@example.com", "hunter2pass").status_code == 401
    assert _login(client, "samuel@example.com", "hunter2pass").status_code == 200
    assert client.get("/profile", headers=headers).json()["email"] == "samuel@example.com"


def test_change_email_requires_correct_current_password(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = client.put(
        "/profile/email",
        json={"new_email": "samuel@example.com", "current_password": "wrongpass"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "current password" in resp.json()["detail"].lower()


def test_change_email_rejects_same_email(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = client.put(
        "/profile/email",
        json={"new_email": "sam@example.com", "current_password": "hunter2pass"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_change_email_rejects_email_in_use(client, make_user):
    make_user(email="taken@example.com")
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = client.put(
        "/profile/email",
        json={"new_email": "taken@example.com", "current_password": "hunter2pass"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_change_email_rejects_invalid_email(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = client.put(
        "/profile/email",
        json={"new_email": "not-an-email", "current_password": "hunter2pass"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_main_admin_email_cannot_be_changed(client, admin_headers):
    resp = client.put(
        "/profile/email",
        json={"new_email": "other@example.com", "current_password": "admin@123"},
        headers=admin_headers,
    )
    assert resp.status_code == 403
    assert client.get("/profile", headers=admin_headers).json()["email"] == "admin123@gmail.com"


# --- password ----------------------------------------------------------------


def _change_password(client, headers, current, new, confirm=None):
    return client.put(
        "/profile/password",
        json={"current_password": current, "new_password": new, "confirm_new_password": confirm or new},
        headers=headers,
    )


def test_change_password(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    assert _change_password(client, headers, "hunter2pass", "brandnewpass1").status_code == 204
    assert _login(client, "sam@example.com", "hunter2pass").status_code == 401
    assert _login(client, "sam@example.com", "brandnewpass1").status_code == 200


def test_new_password_cannot_be_same_as_previous(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = _change_password(client, headers, "hunter2pass", "hunter2pass")
    assert resp.status_code == 400
    assert "different" in resp.json()["detail"].lower()
    # Unchanged: the old password still works.
    assert _login(client, "sam@example.com", "hunter2pass").status_code == 200


def test_change_password_requires_correct_current_password(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = _change_password(client, headers, "wrongpass", "brandnewpass1")
    assert resp.status_code == 400
    assert _login(client, "sam@example.com", "hunter2pass").status_code == 200


def test_change_password_confirmation_must_match(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    resp = _change_password(client, headers, "hunter2pass", "brandnewpass1", confirm="somethingelse1")
    assert resp.status_code == 422
    assert any(e["field"] == "confirm_new_password" for e in resp.json()["errors"])


def test_change_password_minimum_length(client, make_user):
    headers, _ = make_user(email="sam@example.com", password="hunter2pass")
    assert _change_password(client, headers, "hunter2pass", "short").status_code == 422


def test_new_password_is_stored_hashed(client, make_user):
    from app.models import User
    from tests.conftest import TestingSessionLocal

    headers, user = make_user(email="sam@example.com", password="hunter2pass")
    _change_password(client, headers, "hunter2pass", "brandnewpass1")
    db = TestingSessionLocal()
    stored = db.get(User, user["id"]).hashed_password
    db.close()
    assert stored != "brandnewpass1"
    assert stored.startswith("$2b$")


def test_main_admin_can_change_own_password(client, admin_headers):
    assert _change_password(client, admin_headers, "admin@123", "newadminpass1").status_code == 204
    assert _login(client, "admin123@gmail.com", "admin@123").status_code == 401
    assert _login(client, "admin123@gmail.com", "newadminpass1").status_code == 200


def test_admin_password_reset_also_rejects_same_password(client, admin_headers, make_user):
    _, student = make_user(email="sam@example.com", password="hunter2pass")
    resp = client.patch(f"/admin/users/{student['id']}", json={"password": "hunter2pass"}, headers=admin_headers)
    assert resp.status_code == 400
