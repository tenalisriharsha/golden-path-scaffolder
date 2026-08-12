import pytest

from goldpath.flavors import UnknownFlavorError, get_flavor, list_flavors


def test_registry_contains_both_flavors():
    assert {f.name for f in list_flavors()} == {"fastapi", "go"}


def test_get_flavor_is_case_insensitive():
    assert get_flavor("FastAPI").name == "fastapi"
    assert get_flavor(" GO ").name == "go"


def test_flavor_metadata():
    fastapi = get_flavor("fastapi")
    assert fastapi.language == "Python"
    assert fastapi.default_port == 8000
    assert fastapi.health_path == "/healthz"

    go = get_flavor("go")
    assert go.language == "Go"
    assert go.default_port == 8080


def test_unknown_flavor_lists_available():
    with pytest.raises(UnknownFlavorError, match="available: fastapi, go"):
        get_flavor("rust")


def test_list_flavors_is_sorted():
    names = [f.name for f in list_flavors()]
    assert names == sorted(names)
