"""Registry of service flavors the scaffolder can generate."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Flavor", "UnknownFlavorError", "get_flavor", "list_flavors"]


class UnknownFlavorError(Exception):
    """Raised when a requested flavor is not in the registry."""


@dataclass(frozen=True)
class Flavor:
    """Metadata describing one service flavor."""

    name: str
    language: str
    default_port: int
    description: str
    health_path: str = "/healthz"


_FLAVORS: dict[str, Flavor] = {
    "fastapi": Flavor(
        name="fastapi",
        language="Python",
        default_port=8000,
        description="FastAPI service with uvicorn, ready for containerization.",
    ),
    "go": Flavor(
        name="go",
        language="Go",
        default_port=8080,
        description="Go service using net/http, ready for containerization.",
    ),
}


def list_flavors() -> list[Flavor]:
    """Return all registered flavors, sorted by name."""
    return sorted(_FLAVORS.values(), key=lambda f: f.name)


def get_flavor(name: str) -> Flavor:
    """Look up a flavor by name (case-insensitive).

    Raises :class:`UnknownFlavorError` listing the available flavors.
    """
    flavor = _FLAVORS.get(name.strip().lower())
    if flavor is None:
        available = ", ".join(f.name for f in list_flavors())
        raise UnknownFlavorError(f"unknown flavor {name!r}; available: {available}")
    return flavor
