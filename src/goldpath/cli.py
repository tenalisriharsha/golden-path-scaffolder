"""Command-line interface for golden-path-scaffolder.

Usage:
    goldpath list
    goldpath new <service-name> --flavor <flavor> [--output DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import flavors, scaffold
from .engine import TemplateError

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="goldpath",
        description="Scaffold a production-ready service on the golden path.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available service flavors.")

    new = sub.add_parser("new", help="Generate a new service.")
    new.add_argument("name", help="Service name (lowercase, e.g. orders-api).")
    new.add_argument("--flavor", required=True, help="Service flavor (see `goldpath list`).")
    new.add_argument(
        "--output",
        default=".",
        help="Directory to create the service in (default: current directory).",
    )
    new.add_argument(
        "--no-k8s",
        dest="with_k8s",
        action="store_false",
        help="Skip Kubernetes manifests and the Grafana dashboard.",
    )
    return parser


def _cmd_list() -> int:
    for flavor in flavors.list_flavors():
        print(f"{flavor.name:<10} {flavor.language:<8} port {flavor.default_port:<5} {flavor.description}")
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    try:
        flavor = flavors.get_flavor(args.flavor)
        written = scaffold.scaffold_service(
            args.name, flavor, Path(args.output), with_k8s=args.with_k8s
        )
    except (flavors.UnknownFlavorError, scaffold.ScaffoldError, TemplateError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Scaffolded {args.name!r} ({flavor.name}) with {len(written)} files:")
    for path in written:
        print(f"  {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "list":
        return _cmd_list()
    return _cmd_new(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
