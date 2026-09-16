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
