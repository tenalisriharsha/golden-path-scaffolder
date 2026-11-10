import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("{{ health_path }}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "{{ service_name }}"}


def test_metrics_exposed():
    client.get("{{ health_path }}")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "{{ service_slug }}_requests_total" in response.text


def test_counter_increments_on_unhandled_exception():
    @app.get("/__boom_test__")
    def boom():
        raise RuntimeError("boom")

    boom_client = TestClient(app, raise_server_exceptions=False)
    response = boom_client.get("/__boom_test__")
    assert response.status_code == 500

    metrics = client.get("/metrics").text
    assert 'path="/__boom_test__"' in metrics
    assert 'status_code="500"' in metrics


def test_metric_cardinality_bounded_for_unmatched_paths():
    random_paths = [
        "/users/12345",
        "/scan/wp-admin.php",
        "/api/v2/orders/abc-def-ghi",
        "/nonexistent-" + "x" * 40,
    ]
    for path in random_paths:
        client.get(path)

    metrics_text = client.get("/metrics").text
    counter_name = "{{ service_slug }}_requests_total"
    leaked_raw_paths = set()
    for line in metrics_text.splitlines():
        if not line.startswith(counter_name):
            continue
        match = re.search(r'path="([^"]*)"', line)
        if match and match.group(1) in random_paths:
            leaked_raw_paths.add(match.group(1))

    assert not leaked_raw_paths, (
        "unmatched request paths must not appear verbatim as metric labels "
        f"(unbounded cardinality): {leaked_raw_paths}"
    )
