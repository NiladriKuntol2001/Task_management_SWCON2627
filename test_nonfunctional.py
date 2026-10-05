"""Non-functional checks that can run without a browser (NFR-01, NFR-10..NFR-13)."""
import importlib
import time

import pytest

from .helpers import future_deadline, make_task


def test_TC_NFR_01_api_responds_within_2_seconds_with_100_tasks(client, auth_headers):
    for i in range(100):
        assert make_task(client, auth_headers, title=f"t{i}", subject=f"s{i % 5}",
                         deadline=future_deadline(days=1 + i % 20)).status_code == 201
    slowest = 0.0
    for url in ("/tasks", "/tasks?sort_by=deadline", "/tasks/upcoming", "/dashboard", "/tasks?subject=s1"):
        for _ in range(10):
            start = time.perf_counter()
            assert client.get(url, headers=auth_headers).status_code == 200
            slowest = max(slowest, time.perf_counter() - start)
    print(f"slowest response: {slowest * 1000:.0f} ms")
    assert slowest < 2.0


def test_TC_NFR_06_malformed_requests_get_a_clear_error_and_server_survives(client, auth_headers):
    r = client.post("/tasks", content="{ this is not json", headers={**auth_headers, "Content-Type": "application/json"})
    assert r.status_code == 422 and r.json()["detail"]
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/tasks/does-not-exist", headers=auth_headers).status_code == 404


@pytest.mark.parametrize(
    "module",
    ["app.routers.auth", "app.routers.tasks", "app.routers.dashboard", "app.priority", "app.security"],
)
def test_TC_NFR_07_major_components_are_separate_modules(module):
    assert importlib.import_module(module)


def test_TC_NFR_07b_priority_module_does_not_depend_on_the_web_layer():
    import app.priority as priority
    source = open(priority.__file__).read()
    assert "fastapi" not in source and "sqlalchemy" not in source
