"""Generation pipeline: render a flavor's template tree into a new service."""

from __future__ import annotations

import re
from pathlib import Path

from . import engine
from .flavors import Flavor

__all__ = ["ScaffoldError", "scaffold_service", "validate_service_name"]

_NAME = re.compile(r"^[a-z][a-z0-9-]{0,62}$")

_TEMPLATES_ROOT = Path(__file__).resolve().parent / "templates"


class ScaffoldError(Exception):
    """Raised when a service cannot be generated."""


def validate_service_name(name: str) -> str:
    """Return *name* if it is a valid service name, else raise ScaffoldError.

    Valid names are lowercase DNS-label style: start with a letter, then
    letters, digits, or hyphens (max 63 chars) — safe for k8s and image names.
    """
    if not _NAME.match(name):
        raise ScaffoldError(
            f"invalid service name {name!r}: use lowercase letters, digits and "
            "hyphens, starting with a letter (max 63 chars)"
        )
    return name


# Template subtrees that are only written when the platform-asset flag is on.
_K8S_DIRS = ("k8s", "grafana")


def build_context(name: str, flavor: Flavor, *, with_k8s: bool = True) -> dict[str, object]:
    """Build the template context for a service."""
    return {
        "service_name": name,
        "service_slug": name.replace("-", "_"),
        "flavor": flavor.name,
        "language": flavor.language,
        "port": flavor.default_port,
        "health_path": flavor.health_path,
        "with_k8s": with_k8s,
    }


def scaffold_service(
    name: str,
    flavor: Flavor,
    output_dir: Path | str,
    *,
    template_root: Path | None = None,
    with_k8s: bool = True,
) -> list[Path]:
    """Generate a new service named *name* from *flavor* into *output_dir*.

    The service is written to ``output_dir / name``. Every file in the
    flavor's template tree is rendered through the template engine; the
    relative path structure is preserved.

    If *with_k8s* is false, the Kubernetes manifests and Grafana dashboard
    (the ``k8s/`` and ``grafana/`` subtrees) are skipped, and any
    ``{% if with_k8s %}`` sections in other templates render empty.

    Returns the sorted list of written file paths.
    """
    validate_service_name(name)
    root = (template_root or _TEMPLATES_ROOT) / flavor.name
    if not root.is_dir():
        raise ScaffoldError(f"template tree for flavor {flavor.name!r} not found at {root}")

    target = Path(output_dir) / name
    if target.exists():
        raise ScaffoldError(f"target directory already exists: {target}")

    context = build_context(name, flavor, with_k8s=with_k8s)
    written: list[Path] = []
    for source in sorted(root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(root)
        if not with_k8s and relative.parts[0] in _K8S_DIRS:
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(engine.render(source.read_text(), context))
        written.append(destination)
    return sorted(written)
