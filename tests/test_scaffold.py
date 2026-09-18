import json

import pytest

from goldpath.flavors import get_flavor
from goldpath.scaffold import (
    ScaffoldError,
    build_context,
    scaffold_service,
    validate_service_name,
)


def test_build_context_derives_metric_safe_slug():
    context = build_context("orders-api", get_flavor("fastapi"))
    assert context["service_slug"] == "orders_api"
    assert context["service_name"] == "orders-api"


def test_validate_service_name_accepts_dns_style():
    for name in ("api", "orders-api", "svc-2", "a" * 63):
        assert validate_service_name(name) == name


@pytest.mark.parametrize("name", ["", "API", "-api", "my_svc", "a b", "a" * 64])
def test_validate_service_name_rejects_invalid(name):
    with pytest.raises(ScaffoldError, match="invalid service name"):
        validate_service_name(name)


def test_scaffold_fastapi_service(tmp_path):
    written = scaffold_service("orders-api", get_flavor("fastapi"), tmp_path)
    root = tmp_path / "orders-api"
    assert root.is_dir()
    assert (root / "app" / "main.py").is_file()
    assert (root / "requirements.txt").is_file()
    assert len(written) == 13

    main = (root / "app" / "main.py").read_text()
    assert 'title="orders-api"' in main
    assert '"orders-api"' in main
    assert "{{" not in main  # nothing left unrendered


def test_scaffold_fastapi_production_set(tmp_path):
    scaffold_service("orders-api", get_flavor("fastapi"), tmp_path)
    root = tmp_path / "orders-api"

    assert (root / "Dockerfile").is_file()
    assert (root / ".dockerignore").is_file()
    assert (root / ".github" / "workflows" / "ci.yml").is_file()
    assert (root / "requirements-dev.txt").is_file()
    assert (root / "tests" / "test_health.py").is_file()
    assert (root / "conftest.py").is_file()

    main = (root / "app" / "main.py").read_text()
    assert "prometheus_client" in main
    assert "orders_api_requests_total" in main
    assert '"/metrics"' in main

    dockerfile = (root / "Dockerfile").read_text()
    assert "FROM python:3.12-slim AS builder" in dockerfile
    assert "USER appuser" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "{{" not in dockerfile

    ci = (root / ".github" / "workflows" / "ci.yml").read_text()
    assert "pytest" in ci
    assert "ruff check" in ci
    assert "docker build" in ci
    assert "{{" not in ci

    test_health = (root / "tests" / "test_health.py").read_text()
    assert "/healthz" in test_health
    assert "orders_api_requests_total" in test_health
    assert "{{" not in test_health


@pytest.mark.parametrize("flavor_name,name", [("fastapi", "orders-api"), ("go", "payments")])
def test_scaffold_platform_assets(tmp_path, flavor_name, name):
    scaffold_service(name, get_flavor(flavor_name), tmp_path)
    root = tmp_path / name
    slug = name.replace("-", "_")

    deployment = (root / "k8s" / "deployment.yaml").read_text()
    assert f"name: {name}" in deployment
    assert f"image: {name}:latest" in deployment
    assert "livenessProbe" in deployment
    assert "readinessProbe" in deployment
    assert "resources" in deployment
    assert "{{" not in deployment

    service = (root / "k8s" / "service.yaml").read_text()
    assert f"name: {name}" in service
    assert "{{" not in service

    dashboard = (root / "grafana" / "dashboard.json").read_text()
    assert f"{slug}_requests_total" in dashboard
    assert "{{" not in dashboard
    json.loads(dashboard)  # must be valid JSON after rendering

    readme = (root / "README.md").read_text()
    assert "Deploy to Kubernetes" in readme
    assert "kubectl apply -f k8s/" in readme
    assert "grafana/dashboard.json" in readme


@pytest.mark.parametrize("flavor_name", ["fastapi", "go"])
def test_scaffold_without_k8s_skips_platform_assets(tmp_path, flavor_name):
    written = scaffold_service("web", get_flavor(flavor_name), tmp_path, with_k8s=False)
    root = tmp_path / "web"

    assert not (root / "k8s").exists()
    assert not (root / "grafana").exists()
    assert all("k8s" not in p.parts and "grafana" not in p.parts for p in written)

    readme = (root / "README.md").read_text()
    assert "Deploy to Kubernetes" not in readme
    assert "grafana/dashboard.json" not in readme
    assert "{{" not in readme


def test_build_context_with_k8s_flag_defaults_true():
    context = build_context("orders-api", get_flavor("fastapi"))
    assert context["with_k8s"] is True
    context = build_context("orders-api", get_flavor("fastapi"), with_k8s=False)
    assert context["with_k8s"] is False


def test_scaffold_go_service(tmp_path):
    scaffold_service("payments", get_flavor("go"), tmp_path)
    root = tmp_path / "payments"
    main = (root / "cmd" / "server" / "main.go").read_text()
    assert '"payments"' in main
    assert ":8080" in main
    assert (root / "go.mod").read_text().startswith("module payments")


def test_scaffold_go_production_set(tmp_path):
    written = scaffold_service("payments", get_flavor("go"), tmp_path)
    root = tmp_path / "payments"

    assert (root / "Dockerfile").is_file()
    assert (root / ".dockerignore").is_file()
    assert (root / ".github" / "workflows" / "ci.yml").is_file()
    assert (root / "cmd" / "server" / "main_test.go").is_file()
    assert (root / "go.sum").is_file()
    assert len(written) == 11

    main = (root / "cmd" / "server" / "main.go").read_text()
    assert "promhttp" in main
    assert "payments_requests_total" in main
    assert "GET /metrics" in main
    assert "{{" not in main

    dockerfile = (root / "Dockerfile").read_text()
    assert "FROM golang:1.25 AS builder" in dockerfile
    assert "distroless" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert "{{" not in dockerfile

    ci = (root / ".github" / "workflows" / "ci.yml").read_text()
    assert "go vet" in ci
    assert "go test" in ci
    assert "docker build" in ci
    assert "{{" not in ci

    main_test = (root / "cmd" / "server" / "main_test.go").read_text()
    assert "/healthz" in main_test
    assert "payments_requests_total" in main_test
    assert "{{" not in main_test

    go_mod = (root / "go.mod").read_text()
    assert "prometheus/client_golang" in go_mod


def test_scaffold_renders_port_and_health_path(tmp_path):
    scaffold_service("web", get_flavor("fastapi"), tmp_path)
    readme = (tmp_path / "web" / "README.md").read_text()
    assert "8000" in readme
    assert "/healthz" in readme


def test_scaffold_refuses_existing_directory(tmp_path):
    (tmp_path / "orders-api").mkdir()
    with pytest.raises(ScaffoldError, match="already exists"):
        scaffold_service("orders-api", get_flavor("fastapi"), tmp_path)


def test_scaffold_invalid_name_raises_before_writing(tmp_path):
    with pytest.raises(ScaffoldError):
        scaffold_service("Bad Name", get_flavor("go"), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_scaffold_returns_written_paths_sorted(tmp_path):
    written = scaffold_service("web", get_flavor("go"), tmp_path)
    assert written == sorted(written)
    assert all(p.is_file() for p in written)
