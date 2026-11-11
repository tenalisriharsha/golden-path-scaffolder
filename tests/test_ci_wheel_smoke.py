"""Regression test for issue #15.

CI's `wheel-smoke` job builds the wheel, installs it, and scaffolds
both flavors with `goldpath new` -- but today it stops there. It never
runs `go build`/`go test` on the generated Go service, and never runs
`pytest`/`ruff` on the generated FastAPI service. A template change
that renders cleanly but produces code that fails to compile or fails
its own tests would pass CI undetected.

This test parses the actual `.github/workflows/ci.yml` (so it tracks
whatever CI does today rather than a hard-coded guess) and asserts
that, after each `goldpath new` invocation in the `wheel-smoke` job,
there is a later step in that same job which actually builds/tests
the service it just generated, inside that service's own directory.
"""

from __future__ import annotations

import re
from pathlib import Path

CI_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def _wheel_smoke_job_text() -> str:
    text = CI_PATH.read_text()
    match = re.search(r"^  wheel-smoke:\n(.*?)(?=^  \S|\Z)", text, re.S | re.M)
    assert match, "ci.yml must have a top-level `wheel-smoke:` job"
    return match.group(1)


def _run_scripts(job_text: str) -> list[str]:
    """Return the shell script body of every `run: |` step in the job, in order."""
    scripts = []
    for step_match in re.finditer(
        r"run:\s*\|\n((?:[ \t]+\S.*\n?|[ \t]*\n)+)", job_text
    ):
        scripts.append(step_match.group(1))
    return scripts


def test_wheel_smoke_builds_and_tests_the_generated_go_service():
    """CI must actually build/test the Go service it scaffolds, not just generate it."""
    job_text = _wheel_smoke_job_text()
    scripts = _run_scripts(job_text)

    generate_idx = next(
        (i for i, s in enumerate(scripts) if "goldpath new inventory-svc" in s),
        None,
    )
    assert generate_idx is not None, (
        "expected a `run:` step that scaffolds the Go service "
        "(`goldpath new inventory-svc --flavor go`)"
    )

    later_scripts = scripts[generate_idx:]
    combined = "\n".join(later_scripts)

    has_go_build = re.search(r"\bgo build\b", combined)
    has_go_test = re.search(r"\bgo test\b", combined)
    mentions_service_dir = "inventory-svc" in combined

    assert has_go_build and has_go_test and mentions_service_dir, (
        "wheel-smoke scaffolds the Go service with `goldpath new inventory-svc "
        "--flavor go` but never runs `go build`/`go test` against it, so a "
        "template change that fails to compile or fails its own tests would "
        "pass CI undetected"
    )


def test_wheel_smoke_tests_the_generated_fastapi_service():
    """CI must actually run the FastAPI service's own test suite, not just generate it."""
    job_text = _wheel_smoke_job_text()
    scripts = _run_scripts(job_text)

    generate_idx = next(
        (i for i, s in enumerate(scripts) if "goldpath new orders-api" in s),
        None,
    )
    assert generate_idx is not None, (
        "expected a `run:` step that scaffolds the FastAPI service "
        "(`goldpath new orders-api --flavor fastapi`)"
    )

    later_scripts = scripts[generate_idx:]
    combined = "\n".join(later_scripts)

    has_pytest = re.search(r"\bpytest\b", combined)
    mentions_service_dir = "orders-api" in combined

    assert has_pytest and mentions_service_dir, (
        "wheel-smoke scaffolds the FastAPI service with `goldpath new orders-api "
        "--flavor fastapi` but never runs `pytest` against it, so a template "
        "change that fails its own tests would pass CI undetected"
    )
