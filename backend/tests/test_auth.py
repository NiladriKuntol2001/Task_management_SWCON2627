"""Auth: registration, login, logout, password hashing (FR-01/02/03, NFR-03)."""


def test_register_creates_user_and_returns_token(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "hunter2pass"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["name"] == "Alice"
    assert "password" not in body["user"]


def test_register_duplicate_email_rejected(client, make_user):
    make_user(email="dup@example.com")
    resp = client.post(
        "/auth/register",
        json={"name": "Bob", "email": "dup@example.com", "password": "anotherpass1"},
    )
    assert resp.status_code == 409


def test_register_requires_valid_fields(client):
    resp = client.post(
        "/auth/register",
        json={"name": "", "email": "not-an-email", "password": "short"},
    )
    assert resp.status_code == 422


def test_password_is_not_stored_in_plaintext(client):
    from app.database import SessionLocal  # noqa
    from app.models import User

    client.post(
        "/auth/register",
        json={"name": "Carol", "email": "carol@example.com", "password": "hunter2pass"},
    )
    # Pull straight from the DB layer to make sure the stored value is hashed.
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "carol@example.com").first()
    assert user.hashed_password != "hunter2pass"
    assert user.hashed_password.startswith("$2b$")
    db.close()


def test_login_success(client, make_user):
    make_user(email="dana@example.com", password="hunter2pass")
    resp = client.post(
        "/auth/login", json={"email": "dana@example.com", "password": "hunter2pass"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password_rejected(client, make_user):
    make_user(email="erin@example.com", password="hunter2pass")
    resp = client.post(
        "/auth/login", json={"email": "erin@example.com", "password": "wrongpass"}
    )
    assert resp.status_code == 401


def test_login_unknown_email_rejected(client):
    resp = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever1"}
    )
    assert resp.status_code == 401


def test_protected_route_requires_auth(client):
    resp = client.get("/tasks")
    assert resp.status_code == 401


def test_protected_route_rejects_invalid_token(client):
    resp = client.get("/tasks", headers={"Authorization": "Bearer garbage-token"})
    assert resp.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


def test_logout_requires_auth_and_succeeds(client, auth_headers):
    resp = client.post("/auth/logout", headers=auth_headers)
    assert resp.status_code == 204
