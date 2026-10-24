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
