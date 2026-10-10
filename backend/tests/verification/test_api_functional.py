"""Independent API tests derived from the acceptance criteria (Spec sections 6.1-6.18).

Test IDs (TC-AUTH / TC-TASK / TC-PRI / TC-FLT / TC-SORT / TC-UPC / TC-OVD /
TC-DASH / TC-REC) match the traceability matrix in the report.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token
from tests.conftest import TestingSessionLocal

from .helpers import future_deadline, make_task, past_deadline

PROTECTED = [
    ("GET", "/tasks"), ("POST", "/tasks"), ("GET", "/tasks/upcoming"),
    ("GET", "/tasks/some-id"), ("PATCH", "/tasks/some-id"), ("DELETE", "/tasks/some-id"),
    ("POST", "/tasks/some-id/complete"), ("GET", "/dashboard"),
    ("GET", "/auth/me"), ("POST", "/auth/logout"),
]


# ============================ Authentication ================================
def test_TC_AUTH_01_register_valid_returns_token_and_hides_password(client):
    r = client.post("/auth/register", json={"name": "Ann", "email": "ann@example.com", "password": "abcd1234"})
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["user"]["email"] == "ann@example.com"
    assert "password" not in r.text.lower()


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "email": "a@example.com", "password": "abcd1234"},
        {"name": "   ", "email": "a@example.com", "password": "abcd1234"},
    ],
    ids=["empty-name", "blank-name"],
)
def test_TC_AUTH_02_registration_rejects_empty_name(client, payload):
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "name"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "A", "password": "abcd1234"},
        {"name": "A", "email": "a@example.com"},
        {"name": "A", "email": "not-an-email", "password": "abcd1234"},
        {"name": "A", "email": "a@example.com", "password": "short"},
    ],
    ids=["no-email", "no-password", "bad-email", "short-password"],
)
def test_TC_AUTH_03_registration_rejects_missing_or_invalid_fields(client, payload):
    assert client.post("/auth/register", json=payload).status_code == 422


def test_TC_AUTH_04_duplicate_email_rejected(client, make_user):
    make_user(email="dup@example.com")
    r = client.post("/auth/register", json={"name": "B", "email": "dup@example.com", "password": "abcd1234"})
    assert r.status_code == 409


@pytest.mark.xfail(strict=True, reason="DEF-02: email uniqueness is case-sensitive (see defect log)")
def test_TC_AUTH_04b_duplicate_email_is_case_insensitive(client, make_user):
    make_user(email="dup@example.com")
    r = client.post("/auth/register", json={"name": "B", "email": "DUP@example.com", "password": "abcd1234"})
    assert r.status_code == 409


def test_TC_AUTH_05_login_with_correct_credentials(client, make_user):
    make_user(email="l@example.com", password="abcd1234")
    r = client.post("/auth/login", json={"email": "l@example.com", "password": "abcd1234"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_TC_AUTH_06_wrong_password_and_unknown_email_give_the_same_error(client, make_user):
    make_user(email="l@example.com", password="abcd1234")
    wrong = client.post("/auth/login", json={"email": "l@example.com", "password": "nope-nope"})
    unknown = client.post("/auth/login", json={"email": "ghost@example.com", "password": "abcd1234"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # does not reveal which part was wrong


@pytest.mark.parametrize("method, path", PROTECTED)
def test_TC_AUTH_07_protected_routes_need_a_token(client, method, path):
    assert client.request(method, path).status_code == 401


def test_TC_AUTH_08_invalid_expired_and_forged_tokens_rejected(client, make_user):
    headers, user = make_user()
    real = headers["Authorization"].split()[1]
    expired = create_access_token(subject=user["id"], expires_minutes=-5)
    unknown_user = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    tampered = real[:-3] + ("AAA" if not real.endswith("AAA") else "BBB")
    unsigned = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0." + real.split(".")[1] + "."
    for token in (expired, unknown_user, tampered, unsigned, "garbage"):
        r = client.get("/tasks", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, token


def test_TC_AUTH_09_logout_endpoint_accepts_an_authenticated_user(client, auth_headers):
    assert client.post("/auth/logout", headers=auth_headers).status_code == 204


def test_TC_AUTH_10_long_password_does_not_crash(client):
    pw = "x" * 100 + "1"
    r = client.post("/auth/register", json={"name": "L", "email": "long@example.com", "password": pw})
    assert r.status_code == 201
    assert client.post("/auth/login", json={"email": "long@example.com", "password": pw}).status_code == 200


# ========================= Task management / validation =====================
def test_TC_TASK_01_create_task_stores_all_fields_and_a_priority(client, auth_headers):
    r = make_task(client, auth_headers, title="Essay", subject="History", difficulty="Hard", hours=3)
    assert r.status_code == 201
    t = r.json()
    assert (t["title"], t["subject"], t["difficulty"], t["estimated_hours"]) == ("Essay", "History", "Hard", 3)
    assert t["completed"] is False and 0 <= t["priority_score"] <= 100 and t["priority_level"]
    assert client.get("/tasks", headers=auth_headers).json()[0]["id"] == t["id"]


@pytest.mark.parametrize("title", ["", "   ", "x" * 201], ids=["empty", "blank", "201-chars"])
def test_TC_TASK_02_invalid_title_rejected_and_not_stored(client, auth_headers, title):
    assert make_task(client, auth_headers, title=title).status_code == 422
    assert client.get("/tasks", headers=auth_headers).json() == []


@pytest.mark.parametrize("subject", ["", "   "])
def test_TC_TASK_03_empty_subject_rejected(client, auth_headers, subject):
    assert make_task(client, auth_headers, subject=subject).status_code == 422
    assert client.get("/tasks", headers=auth_headers).json() == []


@pytest.mark.parametrize("deadline", ["not-a-date", "", None, "2026-13-45"])
def test_TC_TASK_04_invalid_or_missing_deadline_rejected(client, auth_headers, deadline):
    body = {"title": "T", "subject": "S", "difficulty": "Easy", "estimated_hours": 1}
    if deadline is not None:
        body["deadline"] = deadline
    assert client.post("/tasks", json=body, headers=auth_headers).status_code == 422


@pytest.mark.parametrize("hours", [0, -1, -0.5, "abc", None])
def test_TC_TASK_05_estimated_hours_must_be_positive(client, auth_headers, hours):
    assert make_task(client, auth_headers, hours=hours).status_code == 422


def test_TC_TASK_05b_smallest_positive_hours_accepted(client, auth_headers):
    assert make_task(client, auth_headers, hours=0.1).status_code == 201


@pytest.mark.parametrize("difficulty", ["Extreme", "", "easy", 3, None])
def test_TC_TASK_06_invalid_difficulty_rejected(client, auth_headers, difficulty):
    assert make_task(client, auth_headers, difficulty=difficulty).status_code == 422


@pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard", "Very Hard"])
def test_TC_TASK_06b_all_predefined_difficulties_accepted(client, auth_headers, difficulty):
    assert make_task(client, auth_headers, difficulty=difficulty).status_code == 201


def test_TC_TASK_07_edit_own_task_is_saved(client, auth_headers):
    tid = make_task(client, auth_headers, title="Old").json()["id"]
    r = client.patch(f"/tasks/{tid}", json={"title": "New"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["title"] == "New"
    assert client.get(f"/tasks/{tid}", headers=auth_headers).json()["title"] == "New"


@pytest.mark.parametrize(
    "patch",
    [{"title": ""}, {"subject": " "}, {"deadline": "bad"}, {"estimated_hours": 0}, {"difficulty": "Extreme"}],
)
def test_TC_TASK_08_invalid_edit_rejected_and_task_unchanged(client, auth_headers, patch):
    task = make_task(client, auth_headers, title="Keep").json()
    assert client.patch(f"/tasks/{task['id']}", json=patch, headers=auth_headers).status_code == 422
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).json()["title"] == "Keep"


@pytest.mark.parametrize("field", ["title", "subject", "deadline", "difficulty", "estimated_hours"])
@pytest.mark.xfail(strict=True, reason="DEF-01: PATCH with an explicit null returns HTTP 500 (see defect log)")
def test_TC_TASK_08b_explicit_null_must_not_crash_the_server(auth_headers, field):
    """A required field sent as null must be rejected (4xx), never a 500."""
    safe = TestClient(app, raise_server_exceptions=False)
    tid = make_task(safe, auth_headers).json()["id"]
    r = safe.patch(f"/tasks/{tid}", json={field: None}, headers=auth_headers)
    assert r.status_code < 500, f"PATCH {field}=null -> {r.status_code}"
    assert safe.get(f"/tasks/{tid}", headers=auth_headers).status_code == 200  # still readable


def test_TC_TASK_09_delete_removes_the_task_everywhere(client, auth_headers):
    tid = make_task(client, auth_headers).json()["id"]
    assert client.delete(f"/tasks/{tid}", headers=auth_headers).status_code == 204
    assert client.get(f"/tasks/{tid}", headers=auth_headers).status_code == 404
    assert client.get("/tasks", headers=auth_headers).json() == []
    assert client.get("/tasks/upcoming", headers=auth_headers).json() == []
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"] is None


def test_TC_TASK_10_complete_keeps_the_task_and_can_be_reopened(client, auth_headers):
    tid = make_task(client, auth_headers).json()["id"]
    done = client.post(f"/tasks/{tid}/complete", headers=auth_headers).json()
    assert done["completed"] is True
    assert [t["id"] for t in client.get("/tasks?completed=true", headers=auth_headers).json()] == [tid]
    reopened = client.patch(f"/tasks/{tid}", json={"completed": False}, headers=auth_headers).json()
    assert reopened["completed"] is False


def test_TC_TASK_11_task_details_contain_every_field(client, auth_headers):
    tid = make_task(client, auth_headers).json()["id"]
    t = client.get(f"/tasks/{tid}", headers=auth_headers).json()
    for key in ("title", "subject", "deadline", "difficulty", "estimated_hours",
                "completed", "priority_score", "priority_level"):
        assert key in t


def test_TC_TASK_12_tasks_persist_across_logout_and_login(client, make_user):
    headers, _ = make_user(email="p@example.com", password="abcd1234")
    tid = make_task(client, headers, title="Persist").json()["id"]
    client.post("/auth/logout", headers=headers)
    token = client.post("/auth/login", json={"email": "p@example.com", "password": "abcd1234"}).json()["access_token"]
    tasks = client.get("/tasks", headers={"Authorization": f"Bearer {token}"}).json()
    assert [t["id"] for t in tasks] == [tid] and tasks[0]["title"] == "Persist"


def test_TC_TASK_13_validation_errors_name_the_field_and_explain(client, auth_headers):
    r = make_task(client, auth_headers, title="", hours=0)
    errors = r.json()["errors"]
    assert {e["field"] for e in errors} >= {"title", "estimated_hours"}
    assert all(e["message"] for e in errors)


# ============================ Priority via the API ==========================
def test_TC_PRI_11_changing_the_deadline_recalculates_priority(client, auth_headers):
    t = make_task(client, auth_headers, deadline=future_deadline(days=10), difficulty="Very Hard", hours=10).json()
    assert t["priority_score"] == pytest.approx(62.5)  # E5
    t2 = client.patch(f"/tasks/{t['id']}", json={"deadline": future_deadline(hours=12)}, headers=auth_headers).json()
    assert t2["priority_score"] == pytest.approx(100) and t2["priority_level"] == "Critical"


def test_TC_PRI_12_changing_the_difficulty_recalculates_priority(client, auth_headers):
    t = make_task(client, auth_headers, deadline=future_deadline(days=30), difficulty="Easy", hours=1).json()
    assert t["priority_score"] == pytest.approx(13)  # E2
    t2 = client.patch(f"/tasks/{t['id']}", json={"difficulty": "Very Hard"}, headers=auth_headers).json()
    assert t2["priority_score"] == pytest.approx(37)  # 5 + 30 + 2


def test_TC_PRI_13_changing_the_hours_recalculates_priority(client, auth_headers):
    t = make_task(client, auth_headers, deadline=future_deadline(days=30), difficulty="Easy", hours=1).json()
    t2 = client.patch(f"/tasks/{t['id']}", json={"estimated_hours": 10}, headers=auth_headers).json()
    assert t2["priority_score"] == pytest.approx(31)  # 5 + 6 + 20


def test_TC_PRI_15_overdue_task_gets_deadline_score_100(client, auth_headers):
    t = make_task(client, auth_headers, deadline=past_deadline(days=1), difficulty="Easy", hours=1).json()
    assert t["priority_score"] == pytest.approx(58) and t["priority_level"] == "Medium"  # E6


# ======================= Filtering / sorting / tie-break ====================
def _seed_five(client, h):
    spec = {  # E1..E5 from the oracle
        "E1": (dict(hours=12), "Very Hard", 10, "Physics"),
        "E2": (dict(days=30), "Easy", 1, "Math"),
        "E3": (dict(days=4), "Medium", 5, "Math"),
        "E4": (dict(hours=36), "Hard", 8, "Physics"),
        "E5": (dict(days=10), "Very Hard", 10, "Art"),
    }
    ids = {}
    for name, (delta, diff, hours, subject) in spec.items():
        ids[name] = make_task(client, h, title=name, subject=subject, difficulty=diff, hours=hours,
                              deadline=future_deadline(**delta)).json()["id"]
    return ids


def test_TC_FLT_01_filter_by_subject(client, auth_headers):
    _seed_five(client, auth_headers)
    titles = {t["title"] for t in client.get("/tasks?subject=Math", headers=auth_headers).json()}
    assert titles == {"E2", "E3"}


def test_TC_FLT_02_filter_by_completion_status(client, auth_headers):
    ids = _seed_five(client, auth_headers)
    client.post(f"/tasks/{ids['E1']}/complete", headers=auth_headers)
    done = {t["title"] for t in client.get("/tasks?completed=true", headers=auth_headers).json()}
    todo = {t["title"] for t in client.get("/tasks?completed=false", headers=auth_headers).json()}
    assert done == {"E1"} and todo == {"E2", "E3", "E4", "E5"}


def test_TC_FLT_03_filter_with_no_match_and_combined_filters(client, auth_headers):
    ids = _seed_five(client, auth_headers)
    assert client.get("/tasks?subject=Chemistry", headers=auth_headers).json() == []
    client.post(f"/tasks/{ids['E2']}/complete", headers=auth_headers)
    both = client.get("/tasks?subject=Math&completed=false", headers=auth_headers).json()
    assert [t["title"] for t in both] == ["E3"]


def test_TC_SORT_01_sort_by_priority_highest_first(client, auth_headers):
    _seed_five(client, auth_headers)
    tasks = client.get("/tasks?sort_by=priority", headers=auth_headers).json()
    assert [t["title"] for t in tasks] == ["E1", "E4", "E5", "E3", "E2"]
    assert [t["priority_score"] for t in tasks] == pytest.approx([100, 77.5, 62.5, 50, 13])


def test_TC_SORT_02_sort_by_deadline_earliest_first(client, auth_headers):
    _seed_five(client, auth_headers)
    tasks = client.get("/tasks?sort_by=deadline", headers=auth_headers).json()
    assert [t["title"] for t in tasks] == ["E1", "E4", "E3", "E5", "E2"]


def test_TC_SORT_03_equal_scores_earlier_deadline_first(client, auth_headers):
    later = make_task(client, auth_headers, title="later", deadline=future_deadline(days=5)).json()
    sooner = make_task(client, auth_headers, title="sooner", deadline=future_deadline(days=4)).json()
    assert later["priority_score"] == sooner["priority_score"] == 50
    tasks = client.get("/tasks?sort_by=priority", headers=auth_headers).json()
    assert [t["title"] for t in tasks] == ["sooner", "later"]


def test_TC_SORT_04_equal_score_and_deadline_oldest_task_first(client, auth_headers):
    """Team decision D2: same priority score AND same deadline -> the task created earlier comes first."""
    d = future_deadline(days=4)
    for name in ("first", "second", "third"):
        make_task(client, auth_headers, title=name, deadline=d)
    for _ in range(3):
        titles = [t["title"] for t in client.get("/tasks", headers=auth_headers).json()]
        assert titles == ["first", "second", "third"]


# ====================== Upcoming / overdue / dashboard ======================
def test_TC_UPC_01_upcoming_shows_next_7_days_earliest_first(client, auth_headers):
    a = make_task(client, auth_headers, title="2d", deadline=future_deadline(days=2)).json()["id"]
    b = make_task(client, auth_headers, title="6d", deadline=future_deadline(days=6)).json()["id"]
    make_task(client, auth_headers, title="10d", deadline=future_deadline(days=10))
    ids = [t["id"] for t in client.get("/tasks/upcoming", headers=auth_headers).json()]
    assert a in ids and b in ids and ids.index(a) < ids.index(b)
    assert all(t["title"] != "10d" for t in client.get("/tasks/upcoming", headers=auth_headers).json())


def test_TC_UPC_02_completed_tasks_not_upcoming(client, auth_headers):
    tid = make_task(client, auth_headers, deadline=future_deadline(days=2)).json()["id"]
    client.post(f"/tasks/{tid}/complete", headers=auth_headers)
    assert client.get("/tasks/upcoming", headers=auth_headers).json() == []


@pytest.mark.xfail(strict=True, reason="DEF-03: overdue tasks are listed as upcoming (decision D3 says they must not be)")
def test_TC_UPC_03_overdue_tasks_not_listed_as_upcoming(client, auth_headers):
    """Team decision D3: FR-17 lists only tasks due in the next 7 days; overdue tasks belong to FR-18."""
    make_task(client, auth_headers, title="late", deadline=past_deadline(days=1))
    make_task(client, auth_headers, title="soon", deadline=future_deadline(days=2))
    titles = [t["title"] for t in client.get("/tasks/upcoming", headers=auth_headers).json()]
    assert titles == ["soon"]
    dash = client.get("/dashboard", headers=auth_headers).json()
    assert [t["title"] for t in dash["upcoming_tasks"]] == ["soon"]
    assert dash["upcoming_count"] == 1
    assert [t["title"] for t in dash["overdue_tasks"]] == ["late"]


def test_TC_OVD_01_incomplete_task_past_deadline_is_overdue(client, auth_headers):
    make_task(client, auth_headers, title="late", deadline=past_deadline(hours=2))
    make_task(client, auth_headers, title="fine", deadline=future_deadline(days=2))
    tasks = {t["title"]: t for t in client.get("/tasks", headers=auth_headers).json()}
    assert tasks["late"]["is_overdue"] is True and tasks["fine"]["is_overdue"] is False
    only = client.get("/tasks?overdue_only=true", headers=auth_headers).json()
    assert [t["title"] for t in only] == ["late"]


def test_TC_OVD_02_completed_task_is_never_overdue(client, auth_headers):
    tid = make_task(client, auth_headers, deadline=past_deadline(days=3)).json()["id"]
    done = client.post(f"/tasks/{tid}/complete", headers=auth_headers).json()
    assert done["is_overdue"] is False
    assert client.get("/tasks?overdue_only=true", headers=auth_headers).json() == []


def test_TC_DASH_01_dashboard_summarises_the_task_mix(client, auth_headers):
    make_task(client, auth_headers, title="crit", deadline=future_deadline(hours=12), difficulty="Very Hard", hours=10)
    make_task(client, auth_headers, title="med", deadline=future_deadline(days=4))
    make_task(client, auth_headers, title="late", deadline=past_deadline(days=1), difficulty="Easy", hours=1)
    tid = make_task(client, auth_headers, title="done").json()["id"]
    client.post(f"/tasks/{tid}/complete", headers=auth_headers)
    d = client.get("/dashboard", headers=auth_headers).json()
    assert d["incomplete_count"] == 3 and d["completed_count"] == 1
    assert d["high_priority_count"] == 1  # only "crit" is High/Critical
    assert d["overdue_count"] == 1
    assert {t["title"] for t in d["upcoming_tasks"]} >= {"crit", "med"}
    assert d["recommended_task"]["title"] == "crit"


# =========================== Daily recommendation ===========================
def test_TC_REC_01_recommends_the_highest_priority_incomplete_task(client, auth_headers):
    _seed_five(client, auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "E1"


def test_TC_REC_02_completed_tasks_are_excluded_from_the_recommendation(client, auth_headers):
    ids = _seed_five(client, auth_headers)
    client.post(f"/tasks/{ids['E1']}/complete", headers=auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "E4"
    client.patch(f"/tasks/{ids['E1']}", json={"completed": False}, headers=auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "E1"


def test_TC_REC_03_equal_scores_recommend_the_earlier_deadline(client, auth_headers):
    make_task(client, auth_headers, title="later", deadline=future_deadline(days=5))
    sooner = make_task(client, auth_headers, title="sooner", deadline=future_deadline(days=4)).json()
    rec = client.get("/dashboard", headers=auth_headers).json()["recommended_task"]
    assert rec["id"] == sooner["id"]


def test_TC_REC_04_no_incomplete_tasks_gives_no_recommendation(client, auth_headers):
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"] is None
    tid = make_task(client, auth_headers).json()["id"]
    client.post(f"/tasks/{tid}/complete", headers=auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"] is None


def test_TC_REC_05_overdue_tasks_can_be_recommended(client, auth_headers):
    make_task(client, auth_headers, title="late", deadline=past_deadline(days=2), difficulty="Very Hard", hours=10)
    make_task(client, auth_headers, title="easy", deadline=future_deadline(days=30), difficulty="Easy", hours=1)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "late""""Independent API tests derived from the acceptance criteria (Spec sections 6.1-6.18).

Test IDs (TC-AUTH / TC-TASK / TC-PRI / TC-FLT / TC-SORT / TC-UPC / TC-OVD /
TC-DASH / TC-REC) match the traceability matrix in the report.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token
from tests.conftest import TestingSessionLocal

from .helpers import future_deadline, make_task, past_deadline

PROTECTED = [
    ("GET", "/tasks"), ("POST", "/tasks"), ("GET", "/tasks/upcoming"),
    ("GET", "/tasks/some-id"), ("PATCH", "/tasks/some-id"), ("DELETE", "/tasks/some-id"),
    ("POST", "/tasks/some-id/complete"), ("GET", "/dashboard"),
    ("GET", "/auth/me"), ("POST", "/auth/logout"),
]


# ============================ Authentication ================================
def test_TC_AUTH_01_register_valid_returns_token_and_hides_password(client):
    r = client.post("/auth/register", json={"name": "Ann", "email": "ann@example.com", "password": "abcd1234"})
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["user"]["email"] == "ann@example.com"
    assert "password" not in r.text.lower()


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "email": "a@example.com", "password": "abcd1234"},
        {"name": "   ", "email": "a@example.com", "password": "abcd1234"},
    ],
    ids=["empty-name", "blank-name"],
)
def test_TC_AUTH_02_registration_rejects_empty_name(client, payload):
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "name"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "A", "password": "abcd1234"},
        {"name": "A", "email": "a@example.com"},
        {"name": "A", "email": "not-an-email", "password": "abcd1234"},
        {"name": "A", "email": "a@example.com", "password": "short"},
    ],
    ids=["no-email", "no-password", "bad-email", "short-password"],
)
def test_TC_AUTH_03_registration_rejects_missing_or_invalid_fields(client, payload):
    assert client.post("/auth/register", json=payload).status_code == 422


def test_TC_AUTH_04_duplicate_email_rejected(client, make_user):
    make_user(email="dup@example.com")
    r = client.post("/auth/register", json={"name": "B", "email": "dup@example.com", "password": "abcd1234"})
    assert r.status_code == 409


@pytest.mark.xfail(strict=True, reason="DEF-02: email uniqueness is case-sensitive (see defect log)")
def test_TC_AUTH_04b_duplicate_email_is_case_insensitive(client, make_user):
    make_user(email="dup@example.com")
    r = client.post("/auth/register", json={"name": "B", "email": "DUP@example.com", "password": "abcd1234"})
    assert r.status_code == 409


def test_TC_AUTH_05_login_with_correct_credentials(client, make_user):
    make_user(email="l@example.com", password="abcd1234")
    r = client.post("/auth/login", json={"email": "l@example.com", "password": "abcd1234"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_TC_AUTH_06_wrong_password_and_unknown_email_give_the_same_error(client, make_user):
    make_user(email="l@example.com", password="abcd1234")
    wrong = client.post("/auth/login", json={"email": "l@example.com", "password": "nope-nope"})
    unknown = client.post("/auth/login", json={"email": "ghost@example.com", "password": "abcd1234"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # does not reveal which part was wrong


@pytest.mark.parametrize("method, path", PROTECTED)
def test_TC_AUTH_07_protected_routes_need_a_token(client, method, path):
    assert client.request(method, path).status_code == 401


def test_TC_AUTH_08_invalid_expired_and_forged_tokens_rejected(client, make_user):
    headers, user = make_user()
    real = headers["Authorization"].split()[1]
    expired = create_access_token(subject=user["id"], expires_minutes=-5)
    unknown_user = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    tampered = real[:-3] + ("AAA" if not real.endswith("AAA") else "BBB")
    unsigned = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0." + real.split(".")[1] + "."
    for token in (expired, unknown_user, tampered, unsigned, "garbage"):
        r = client.get("/tasks", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, token


def test_TC_AUTH_09_logout_endpoint_accepts_an_authenticated_user(client, auth_headers):
    assert client.post("/auth/logout", headers=auth_headers).status_code == 204


def test_TC_AUTH_10_long_password_does_not_crash(client):
    pw = "x" * 100 + "1"
    r = client.post("/auth/register", json={"name": "L", "email": "long@example.com", "password": pw})
    assert r.status_code == 201
    assert client.post("/auth/login", json={"email": "long@example.com", "password": pw}).status_code == 200


# ========================= Task management / validation =====================
def test_TC_TASK_01_create_task_stores_all_fields_and_a_priority(client, auth_headers):
    r = make_task(client, auth_headers, title="Essay", subject="History", difficulty="Hard", hours=3)
    assert r.status_code == 201
    t = r.json()
    assert (t["title"], t["subject"], t["difficulty"], t["estimated_hours"]) == ("Essay", "History", "Hard", 3)
    assert t["completed"] is False and 0 <= t["priority_score"] <= 100 and t["priority_level"]
    assert client.get("/tasks", headers=auth_headers).json()[0]["id"] == t["id"]


@pytest.mark.parametrize("title", ["", "   ", "x" * 201], ids=["empty", "blank", "201-chars"])
def test_TC_TASK_02_invalid_title_rejected_and_not_stored(client, auth_headers, title):
    assert make_task(client, auth_headers, title=title).status_code == 422
    assert client.get("/tasks", headers=auth_headers).json() == []


@pytest.mark.parametrize("subject", ["", "   "])
def test_TC_TASK_03_empty_subject_rejected(client, auth_headers, subject):
    assert make_task(client, auth_headers, subject=subject).status_code == 422
    assert client.get("/tasks", headers=auth_headers).json() == []


@pytest.mark.parametrize("deadline", ["not-a-date", "", None, "2026-13-45"])
def test_TC_TASK_04_invalid_or_missing_deadline_rejected(client, auth_headers, deadline):
    body = {"title": "T", "subject": "S", "difficulty": "Easy", "estimated_hours": 1}
    if deadline is not None:
        body["deadline"] = deadline
    assert client.post("/tasks", json=body, headers=auth_headers).status_code == 422


@pytest.mark.parametrize("hours", [0, -1, -0.5, "abc", None])
def test_TC_TASK_05_estimated_hours_must_be_positive(client, auth_headers, hours):
    assert make_task(client, auth_headers, hours=hours).status_code == 422


def test_TC_TASK_05b_smallest_positive_hours_accepted(client, auth_headers):
    assert make_task(client, auth_headers, hours=0.1).status_code == 201


@pytest.mark.parametrize("difficulty", ["Extreme", "", "easy", 3, None])
def test_TC_TASK_06_invalid_difficulty_rejected(client, auth_headers, difficulty):
    assert make_task(client, auth_headers, difficulty=difficulty).status_code == 422


@pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard", "Very Hard"])
def test_TC_TASK_06b_all_predefined_difficulties_accepted(client, auth_headers, difficulty):
    assert make_task(client, auth_headers, difficulty=difficulty).status_code == 201


def test_TC_TASK_07_edit_own_task_is_saved(client, auth_headers):
    tid = make_task(client, auth_headers, title="Old").json()["id"]
    r = client.patch(f"/tasks/{tid}", json={"title": "New"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["title"] == "New"
    assert client.get(f"/tasks/{tid}", headers=auth_headers).json()["title"] == "New"


@pytest.mark.parametrize(
    "patch",
    [{"title": ""}, {"subject": " "}, {"deadline": "bad"}, {"estimated_hours": 0}, {"difficulty": "Extreme"}],
)
def test_TC_TASK_08_invalid_edit_rejected_and_task_unchanged(client, auth_headers, patch):
    task = make_task(client, auth_headers, title="Keep").json()
    assert client.patch(f"/tasks/{task['id']}", json=patch, headers=auth_headers).status_code == 422
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).json()["title"] == "Keep"


@pytest.mark.parametrize("field", ["title", "subject", "deadline", "difficulty", "estimated_hours"])
@pytest.mark.xfail(strict=True, reason="DEF-01: PATCH with an explicit null returns HTTP 500 (see defect log)")
def test_TC_TASK_08b_explicit_null_must_not_crash_the_server(auth_headers, field):
    """A required field sent as null must be rejected (4xx), never a 500."""
    safe = TestClient(app, raise_server_exceptions=False)
    tid = make_task(safe, auth_headers).json()["id"]
    r = safe.patch(f"/tasks/{tid}", json={field: None}, headers=auth_headers)
    assert r.status_code < 500, f"PATCH {field}=null -> {r.status_code}"
    assert safe.get(f"/tasks/{tid}", headers=auth_headers).status_code == 200  # still readable


def test_TC_TASK_09_delete_removes_the_task_everywhere(client, auth_headers):
    tid = make_task(client, auth_headers).json()["id"]
    assert client.delete(f"/tasks/{tid}", headers=auth_headers).status_code == 204
    assert client.get(f"/tasks/{tid}", headers=auth_headers).status_code == 404
    assert client.get("/tasks", headers=auth_headers).json() == []
    assert client.get("/tasks/upcoming", headers=auth_headers).json() == []
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"] is None


def test_TC_TASK_10_complete_keeps_the_task_and_can_be_reopened(client, auth_headers):
    tid = make_task(client, auth_headers).json()["id"]
    done = client.post(f"/tasks/{tid}/complete", headers=auth_headers).json()
    assert done["completed"] is True
    assert [t["id"] for t in client.get("/tasks?completed=true", headers=auth_headers).json()] == [tid]
    reopened = client.patch(f"/tasks/{tid}", json={"completed": False}, headers=auth_headers).json()
    assert reopened["completed"] is False


def test_TC_TASK_11_task_details_contain_every_field(client, auth_headers):
    tid = make_task(client, auth_headers).json()["id"]
    t = client.get(f"/tasks/{tid}", headers=auth_headers).json()
    for key in ("title", "subject", "deadline", "difficulty", "estimated_hours",
                "completed", "priority_score", "priority_level"):
        assert key in t


def test_TC_TASK_12_tasks_persist_across_logout_and_login(client, make_user):
    headers, _ = make_user(email="p@example.com", password="abcd1234")
    tid = make_task(client, headers, title="Persist").json()["id"]
    client.post("/auth/logout", headers=headers)
    token = client.post("/auth/login", json={"email": "p@example.com", "password": "abcd1234"}).json()["access_token"]
    tasks = client.get("/tasks", headers={"Authorization": f"Bearer {token}"}).json()
    assert [t["id"] for t in tasks] == [tid] and tasks[0]["title"] == "Persist"


def test_TC_TASK_13_validation_errors_name_the_field_and_explain(client, auth_headers):
    r = make_task(client, auth_headers, title="", hours=0)
    errors = r.json()["errors"]
    assert {e["field"] for e in errors} >= {"title", "estimated_hours"}
    assert all(e["message"] for e in errors)


# ============================ Priority via the API ==========================
def test_TC_PRI_11_changing_the_deadline_recalculates_priority(client, auth_headers):
    t = make_task(client, auth_headers, deadline=future_deadline(days=10), difficulty="Very Hard", hours=10).json()
    assert t["priority_score"] == pytest.approx(62.5)  # E5
    t2 = client.patch(f"/tasks/{t['id']}", json={"deadline": future_deadline(hours=12)}, headers=auth_headers).json()
    assert t2["priority_score"] == pytest.approx(100) and t2["priority_level"] == "Critical"


def test_TC_PRI_12_changing_the_difficulty_recalculates_priority(client, auth_headers):
    t = make_task(client, auth_headers, deadline=future_deadline(days=30), difficulty="Easy", hours=1).json()
    assert t["priority_score"] == pytest.approx(13)  # E2
    t2 = client.patch(f"/tasks/{t['id']}", json={"difficulty": "Very Hard"}, headers=auth_headers).json()
    assert t2["priority_score"] == pytest.approx(37)  # 5 + 30 + 2


def test_TC_PRI_13_changing_the_hours_recalculates_priority(client, auth_headers):
    t = make_task(client, auth_headers, deadline=future_deadline(days=30), difficulty="Easy", hours=1).json()
    t2 = client.patch(f"/tasks/{t['id']}", json={"estimated_hours": 10}, headers=auth_headers).json()
    assert t2["priority_score"] == pytest.approx(31)  # 5 + 6 + 20


def test_TC_PRI_15_overdue_task_gets_deadline_score_100(client, auth_headers):
    t = make_task(client, auth_headers, deadline=past_deadline(days=1), difficulty="Easy", hours=1).json()
    assert t["priority_score"] == pytest.approx(58) and t["priority_level"] == "Medium"  # E6


# ======================= Filtering / sorting / tie-break ====================
def _seed_five(client, h):
    spec = {  # E1..E5 from the oracle
        "E1": (dict(hours=12), "Very Hard", 10, "Physics"),
        "E2": (dict(days=30), "Easy", 1, "Math"),
        "E3": (dict(days=4), "Medium", 5, "Math"),
        "E4": (dict(hours=36), "Hard", 8, "Physics"),
        "E5": (dict(days=10), "Very Hard", 10, "Art"),
    }
    ids = {}
    for name, (delta, diff, hours, subject) in spec.items():
        ids[name] = make_task(client, h, title=name, subject=subject, difficulty=diff, hours=hours,
                              deadline=future_deadline(**delta)).json()["id"]
    return ids


def test_TC_FLT_01_filter_by_subject(client, auth_headers):
    _seed_five(client, auth_headers)
    titles = {t["title"] for t in client.get("/tasks?subject=Math", headers=auth_headers).json()}
    assert titles == {"E2", "E3"}


def test_TC_FLT_02_filter_by_completion_status(client, auth_headers):
    ids = _seed_five(client, auth_headers)
    client.post(f"/tasks/{ids['E1']}/complete", headers=auth_headers)
    done = {t["title"] for t in client.get("/tasks?completed=true", headers=auth_headers).json()}
    todo = {t["title"] for t in client.get("/tasks?completed=false", headers=auth_headers).json()}
    assert done == {"E1"} and todo == {"E2", "E3", "E4", "E5"}


def test_TC_FLT_03_filter_with_no_match_and_combined_filters(client, auth_headers):
    ids = _seed_five(client, auth_headers)
    assert client.get("/tasks?subject=Chemistry", headers=auth_headers).json() == []
    client.post(f"/tasks/{ids['E2']}/complete", headers=auth_headers)
    both = client.get("/tasks?subject=Math&completed=false", headers=auth_headers).json()
    assert [t["title"] for t in both] == ["E3"]


def test_TC_SORT_01_sort_by_priority_highest_first(client, auth_headers):
    _seed_five(client, auth_headers)
    tasks = client.get("/tasks?sort_by=priority", headers=auth_headers).json()
    assert [t["title"] for t in tasks] == ["E1", "E4", "E5", "E3", "E2"]
    assert [t["priority_score"] for t in tasks] == pytest.approx([100, 77.5, 62.5, 50, 13])


def test_TC_SORT_02_sort_by_deadline_earliest_first(client, auth_headers):
    _seed_five(client, auth_headers)
    tasks = client.get("/tasks?sort_by=deadline", headers=auth_headers).json()
    assert [t["title"] for t in tasks] == ["E1", "E4", "E3", "E5", "E2"]


def test_TC_SORT_03_equal_scores_earlier_deadline_first(client, auth_headers):
    later = make_task(client, auth_headers, title="later", deadline=future_deadline(days=5)).json()
    sooner = make_task(client, auth_headers, title="sooner", deadline=future_deadline(days=4)).json()
    assert later["priority_score"] == sooner["priority_score"] == 50
    tasks = client.get("/tasks?sort_by=priority", headers=auth_headers).json()
    assert [t["title"] for t in tasks] == ["sooner", "later"]


def test_TC_SORT_04_equal_score_and_deadline_oldest_task_first(client, auth_headers):
    """Team decision D2: same priority score AND same deadline -> the task created earlier comes first."""
    d = future_deadline(days=4)
    for name in ("first", "second", "third"):
        make_task(client, auth_headers, title=name, deadline=d)
    for _ in range(3):
        titles = [t["title"] for t in client.get("/tasks", headers=auth_headers).json()]
        assert titles == ["first", "second", "third"]


# ====================== Upcoming / overdue / dashboard ======================
def test_TC_UPC_01_upcoming_shows_next_7_days_earliest_first(client, auth_headers):
    a = make_task(client, auth_headers, title="2d", deadline=future_deadline(days=2)).json()["id"]
    b = make_task(client, auth_headers, title="6d", deadline=future_deadline(days=6)).json()["id"]
    make_task(client, auth_headers, title="10d", deadline=future_deadline(days=10))
    ids = [t["id"] for t in client.get("/tasks/upcoming", headers=auth_headers).json()]
    assert a in ids and b in ids and ids.index(a) < ids.index(b)
    assert all(t["title"] != "10d" for t in client.get("/tasks/upcoming", headers=auth_headers).json())


def test_TC_UPC_02_completed_tasks_not_upcoming(client, auth_headers):
    tid = make_task(client, auth_headers, deadline=future_deadline(days=2)).json()["id"]
    client.post(f"/tasks/{tid}/complete", headers=auth_headers)
    assert client.get("/tasks/upcoming", headers=auth_headers).json() == []


@pytest.mark.xfail(strict=True, reason="DEF-03: overdue tasks are listed as upcoming (decision D3 says they must not be)")
def test_TC_UPC_03_overdue_tasks_not_listed_as_upcoming(client, auth_headers):
    """Team decision D3: FR-17 lists only tasks due in the next 7 days; overdue tasks belong to FR-18."""
    make_task(client, auth_headers, title="late", deadline=past_deadline(days=1))
    make_task(client, auth_headers, title="soon", deadline=future_deadline(days=2))
    titles = [t["title"] for t in client.get("/tasks/upcoming", headers=auth_headers).json()]
    assert titles == ["soon"]
    dash = client.get("/dashboard", headers=auth_headers).json()
    assert [t["title"] for t in dash["upcoming_tasks"]] == ["soon"]
    assert dash["upcoming_count"] == 1
    assert [t["title"] for t in dash["overdue_tasks"]] == ["late"]


def test_TC_OVD_01_incomplete_task_past_deadline_is_overdue(client, auth_headers):
    make_task(client, auth_headers, title="late", deadline=past_deadline(hours=2))
    make_task(client, auth_headers, title="fine", deadline=future_deadline(days=2))
    tasks = {t["title"]: t for t in client.get("/tasks", headers=auth_headers).json()}
    assert tasks["late"]["is_overdue"] is True and tasks["fine"]["is_overdue"] is False
    only = client.get("/tasks?overdue_only=true", headers=auth_headers).json()
    assert [t["title"] for t in only] == ["late"]


def test_TC_OVD_02_completed_task_is_never_overdue(client, auth_headers):
    tid = make_task(client, auth_headers, deadline=past_deadline(days=3)).json()["id"]
    done = client.post(f"/tasks/{tid}/complete", headers=auth_headers).json()
    assert done["is_overdue"] is False
    assert client.get("/tasks?overdue_only=true", headers=auth_headers).json() == []


def test_TC_DASH_01_dashboard_summarises_the_task_mix(client, auth_headers):
    make_task(client, auth_headers, title="crit", deadline=future_deadline(hours=12), difficulty="Very Hard", hours=10)
    make_task(client, auth_headers, title="med", deadline=future_deadline(days=4))
    make_task(client, auth_headers, title="late", deadline=past_deadline(days=1), difficulty="Easy", hours=1)
    tid = make_task(client, auth_headers, title="done").json()["id"]
    client.post(f"/tasks/{tid}/complete", headers=auth_headers)
    d = client.get("/dashboard", headers=auth_headers).json()
    assert d["incomplete_count"] == 3 and d["completed_count"] == 1
    assert d["high_priority_count"] == 1  # only "crit" is High/Critical
    assert d["overdue_count"] == 1
    assert {t["title"] for t in d["upcoming_tasks"]} >= {"crit", "med"}
    assert d["recommended_task"]["title"] == "crit"


# =========================== Daily recommendation ===========================
def test_TC_REC_01_recommends_the_highest_priority_incomplete_task(client, auth_headers):
    _seed_five(client, auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "E1"


def test_TC_REC_02_completed_tasks_are_excluded_from_the_recommendation(client, auth_headers):
    ids = _seed_five(client, auth_headers)
    client.post(f"/tasks/{ids['E1']}/complete", headers=auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "E4"
    client.patch(f"/tasks/{ids['E1']}", json={"completed": False}, headers=auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "E1"


def test_TC_REC_03_equal_scores_recommend_the_earlier_deadline(client, auth_headers):
    make_task(client, auth_headers, title="later", deadline=future_deadline(days=5))
    sooner = make_task(client, auth_headers, title="sooner", deadline=future_deadline(days=4)).json()
    rec = client.get("/dashboard", headers=auth_headers).json()["recommended_task"]
    assert rec["id"] == sooner["id"]


def test_TC_REC_04_no_incomplete_tasks_gives_no_recommendation(client, auth_headers):
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"] is None
    tid = make_task(client, auth_headers).json()["id"]
    client.post(f"/tasks/{tid}/complete", headers=auth_headers)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"] is None


def test_TC_REC_05_overdue_tasks_can_be_recommended(client, auth_headers):
    make_task(client, auth_headers, title="late", deadline=past_deadline(days=2), difficulty="Very Hard", hours=10)
    make_task(client, auth_headers, title="easy", deadline=future_deadline(days=30), difficulty="Easy", hours=1)
    assert client.get("/dashboard", headers=auth_headers).json()["recommended_task"]["title"] == "late"
