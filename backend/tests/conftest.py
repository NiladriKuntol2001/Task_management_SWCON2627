import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Point the app at an in-memory SQLite DB *before* importing app modules,
# since app.database builds the engine at import time from settings.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# StaticPool: every session shares ONE connection. Without it, each new
# connection to ":memory:" is a brand-new empty database, and the TestClient
# serves requests from a different thread than the test body.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


ROOT_ADMIN_EMAIL = "admin123@gmail.com"
ROOT_ADMIN_PASSWORD = "admin@123"


@pytest.fixture(autouse=True)
def _reset_db():
    """Fresh schema per test, with the main admin (user ID 1) seeded exactly
    as the app does on startup."""
    from app.seed import ensure_root_admin

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    ensure_root_admin(db, ROOT_ADMIN_EMAIL, ROOT_ADMIN_PASSWORD, "Administrator")
    db.close()
    yield


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_user(client):
    """Registers a user and returns (headers, user_json)."""

    def _make(name="Alice Student", email="alice@example.com", password="hunter2pass"):
        resp = client.post(
            "/auth/register", json={"name": name, "email": email, "password": password}
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        headers = {"Authorization": f"Bearer {body['access_token']}"}
        return headers, body["user"]

    return _make


@pytest.fixture
def make_admin(make_user):
    """Registers a user, then promotes it directly in the DB (registration
    can never create an admin). Returns (headers, user_json)."""

    def _make(name="Ada Admin", email="admin@example.com", password="adminpass1"):
        from app.models import User

        headers, user = make_user(name=name, email=email, password=password)
        db = TestingSessionLocal()
        db.query(User).filter(User.id == user["id"]).update({"is_admin": True})
        db.commit()
        db.close()
        return headers, user

    return _make


@pytest.fixture
def admin_headers(client):
    """Logged in as the main administrator (user ID 1)."""
    resp = client.post("/auth/login", json={"email": ROOT_ADMIN_EMAIL, "password": ROOT_ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def auth_headers(make_user):
    headers, _ = make_user()
    return headers


def future_deadline(**kwargs) -> str:
    return (datetime.now(timezone.utc) + timedelta(**kwargs)).isoformat()


def past_deadline(**kwargs) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kwargs)).isoformat()
