import pytest

from goldpath.flavors import get_flavor
from goldpath.scaffold import ScaffoldError, scaffold_service, validate_service_name


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
    assert len(written) == 4

    main = (root / "app" / "main.py").read_text()
    assert 'title="orders-api"' in main
    assert '"orders-api"' in main
    assert "{{" not in main  # nothing left unrendered


def test_scaffold_go_service(tmp_path):
    scaffold_service("payments", get_flavor("go"), tmp_path)
    root = tmp_path / "payments"
    main = (root / "cmd" / "server" / "main.go").read_text()
    assert '"payments"' in main
    assert ":8080" in main
    assert (root / "go.mod").read_text().startswith("module payments")


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
