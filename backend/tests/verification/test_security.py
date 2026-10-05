"""Security and data-isolation tests (FR-21, NFR-03, NFR-04, NFR-05, NFR-06).

User A owns tasks; user B (a different student) tries to reach them.
Test IDs (TC-SEC-xx) match the traceability matrix in the report.
"""
from pathlib import Path

import pytest

from app.models import User
from tests.conftest import TestingSessionLocal

from .helpers import future_deadline, make_task


@pytest.fixture
def two_users(make_user):
    a_headers, a = make_user(name="Alice", email="alice@example.com")
    b_headers, b = make_user(name="Bob", email="bob@example.com")
    return a_headers, a, b_headers, b


def _a_task(client, a_headers):
    return make_task(client, a_headers, title="A-secret", subject="A-subject").json()["id"]


# ------------------ Data isolation: user B against A's task -----------------
def test_TC_SEC_01_other_user_cannot_read_a_task(client, two_users):
    a_h, _, b_h, _ = two_users
    tid = _a_task(client, a_h)
    assert client.get(f"/tasks/{tid}", headers=b_h).status_code == 404


def test_TC_SEC_02_other_user_cannot_edit_a_task(client, two_users):
    a_h, _, b_h, _ = two_users
    tid = _a_task(client, a_h)
    assert client.patch(f"/tasks/{tid}", json={"title": "hacked"}, headers=b_h).status_code == 404
    assert client.get(f"/tasks/{tid}", headers=a_h).json()["title"] == "A-secret"


def test_TC_SEC_03_other_user_cannot_delete_a_task(client, two_users):
    a_h, _, b_h, _ = two_users
    tid = _a_task(client, a_h)
    assert client.delete(f"/tasks/{tid}", headers=b_h).status_code == 404
    assert client.get(f"/tasks/{tid}", headers=a_h).status_code == 200


def test_TC_SEC_04_other_user_cannot_complete_a_task(client, two_users):
    a_h, _, b_h, _ = two_users
    tid = _a_task(client, a_h)
    assert client.post(f"/tasks/{tid}/complete", headers=b_h).status_code == 404
    assert client.get(f"/tasks/{tid}", headers=a_h).json()["completed"] is False


def test_TC_SEC_04b_foreign_and_nonexistent_tasks_look_identical(client, two_users):
    """No information leak: 'not yours' and 'does not exist' give the same answer."""
    a_h, _, b_h, _ = two_users
    tid = _a_task(client, a_h)
    foreign = client.get(f"/tasks/{tid}", headers=b_h)
    missing = client.get("/tasks/00000000-0000-0000-0000-000000000000", headers=b_h)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_TC_SEC_05_no_listing_ever_contains_another_users_tasks(client, two_users):
    a_h, _, b_h, _ = two_users
    make_task(client, a_h, title="A-secret", subject="A-subject", deadline=future_deadline(hours=5))
    make_task(client, b_h, title="B-own", subject="B-subject")
    for url in ("/tasks", "/tasks?subject=A-subject", "/tasks?completed=false",
                "/tasks?overdue_only=true", "/tasks/upcoming", "/tasks/subjects"):
        assert "A-secret" not in client.get(url, headers=b_h).text, url
        assert "A-subject" not in client.get(url, headers=b_h).text, url
    dash = client.get("/dashboard", headers=b_h).json()
    assert dash["recommended_task"]["title"] == "B-own"  # not A's more urgent task
    assert "A-secret" not in str(dash)


def test_TC_SEC_06_owner_cannot_be_forged_in_the_request_body(client, two_users):
    a_h, a, b_h, b = two_users
    created = make_task(client, b_h, owner_id=a["id"], userId=a["id"]).json()
    assert created["owner_id"] == b["id"]
    tid = _a_task(client, a_h)
    client.patch(f"/tasks/{tid}", json={"owner_id": b["id"]}, headers=a_h)
    assert client.get(f"/tasks/{tid}", headers=a_h).json()["owner_id"] == a["id"]


# --------------------------- Injection and XSS -------------------------------
def test_TC_SEC_07_sql_injection_in_login_is_rejected(client, make_user):
    make_user(email="victim@example.com", password="abcd1234")
    for email in ("' OR 1=1 --", "victim@example.com' --"):
        r = client.post("/auth/login", json={"email": email, "password": "x"})
        assert r.status_code in (401, 422) and "access_token" not in r.text
    r = client.post("/auth/login", json={"email": {"$ne": None}, "password": {"$ne": None}})
    assert r.status_code == 422


def test_TC_SEC_07b_sql_injection_in_filters_and_text_fields(client, two_users):
    a_h, _, b_h, _ = two_users
    _a_task(client, a_h)
    leaked = client.get("/tasks", params={"subject": "x' OR '1'='1"}, headers=b_h)
    assert leaked.status_code == 200 and leaked.json() == []
    nasty = "'); DROP TABLE tasks; --"
    assert make_task(client, b_h, title=nasty, subject=nasty).status_code == 201
    assert client.get("/tasks", headers=b_h).json()[0]["title"] == nasty  # table intact, stored as text
    assert client.get("/tasks", headers=a_h).status_code == 200


def test_TC_SEC_08_script_in_task_text_is_returned_as_inert_json(client, auth_headers):
    payload = "<script>alert(1)</script>"
    r = make_task(client, auth_headers, title=payload, subject="<img src=x onerror=alert(1)>")
    assert r.status_code == 201
    listing = client.get("/tasks", headers=auth_headers)
    assert listing.headers["content-type"].startswith("application/json")  # never rendered as HTML
    assert listing.json()[0]["title"] == payload  # stored verbatim; escaping is the UI's job


def test_TC_SEC_08b_frontend_never_injects_raw_html():
    """Static check: React escapes text unless dangerouslySetInnerHTML / innerHTML is used."""
    src = Path(__file__).resolve().parents[3] / "frontend" / "src"
    if not src.exists():
        pytest.skip("frontend sources not present")
    offenders = [str(p) for p in src.rglob("*.ts*")
                 if "dangerouslySetInnerHTML" in p.read_text() or ".innerHTML" in p.read_text()]
    assert offenders == []


# ----------------------- Passwords and account handling ----------------------
def test_TC_SEC_09_passwords_are_hashed_and_never_returned(client, make_user):
    headers, user = make_user(email="h@example.com", password="Sup3rSecret!")
    db = TestingSessionLocal()
    stored = db.query(User).filter(User.email == "h@example.com").one().hashed_password
    db.close()
    assert stored != "Sup3rSecret!" and stored.startswith("$2")  # bcrypt
    for url in ("/auth/me", "/dashboard", "/tasks"):
        text = client.get(url, headers=headers).text
        assert "Sup3rSecret!" not in text and "hashed_password" not in text and stored not in text


def test_TC_SEC_09b_same_password_gives_different_hashes(client, make_user):
    make_user(email="one@example.com", password="samepass1")
    make_user(email="two@example.com", password="samepass1")
    db = TestingSessionLocal()
    mine = ["one@example.com", "two@example.com"]  # ignore other accounts (e.g. the seeded admin)
    hashes = {u.hashed_password for u in db.query(User).filter(User.email.in_(mine)).all()}
    db.close()
    assert len(hashes) == 2  # salted


def test_TC_SEC_11_registration_cannot_create_an_admin(client):
    r = client.post("/auth/register", json={"name": "Eve", "email": "eve@example.com",
                                            "password": "abcd1234", "is_admin": True})
    assert r.status_code == 201 and r.json()["user"]["is_admin"] is False


@pytest.mark.parametrize("path", ["/admin/users", "/admin/tasks", "/admin/stats"])
def test_TC_SEC_12_students_cannot_use_admin_routes(client, auth_headers, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers=auth_headers).status_code == 403


def test_TC_SEC_13_admin_responses_never_expose_password_hashes(client, admin_headers, make_user):
    make_user(name="S", email="s@example.com")
    text = client.get("/admin/users", headers=admin_headers).text
    assert "hashed_password" not in text and "$2b$" not in text


def test_TC_SEC_14_deactivated_user_loses_access(client, make_user, admin_headers):
    headers, user = make_user(email="gone@example.com", password="abcd1234")
    r = client.patch(f"/admin/users/{user['id']}", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 200
    assert client.get("/tasks", headers=headers).status_code == 403
    assert client.post("/auth/login", json={"email": "gone@example.com", "password": "abcd1234"}).status_code == 403
