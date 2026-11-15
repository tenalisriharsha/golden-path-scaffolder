"""Regression test for issue #4.

Docker builds and `kubectl apply` of generated services have never been
exercised -- confirmed by the project's own `DAILY_REPORT.md` ("No live
Docker build or `kubectl apply` verification") and `PROGRESS.md`. CI's
`wheel-smoke` job (fixed for issue #15) scaffolds both flavors and runs
their own unit tests/`go build`, but it never runs `docker build` on the
generated Dockerfile, never applies the generated `k8s/` manifests to a
cluster, and never waits for the resulting pods to become Ready. The
README also claims CI does a "docker build on push/PR" that doesn't
actually exist anywhere in `ci.yml`.

This test parses the actual `.github/workflows/ci.yml` (so it tracks
whatever CI does today rather than a hard-coded guess) and the project's
docs, and asserts that the two "Done when" criteria from the issue are
met: both flavors' images actually get built, and their manifests
actually get applied to a cluster and reach Ready -- with the commands
captured in the docs.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _ci_text() -> str:
    return CI_PATH.read_text()


def _all_run_scripts(ci_text: str) -> list[str]:
    """Return the shell script body of every `run: |` step in the whole workflow, in order."""
    return [m.group(1) for m in re.finditer(r"run:\s*\|\n((?:[ \t]+\S.*\n?|[ \t]*\n)+)", ci_text)]


def test_ci_builds_the_docker_image_for_both_generated_flavors():
    """CI must actually run `docker build` against each generated Dockerfile."""
    ci_text = _ci_text()
    scripts = _all_run_scripts(ci_text)

    fastapi_generate_idx = next(
        (i for i, s in enumerate(scripts) if "goldpath new orders-api" in s), None
    )
    go_generate_idx = next(
        (i for i, s in enumerate(scripts) if "goldpath new inventory-svc" in s), None
    )
    assert fastapi_generate_idx is not None and go_generate_idx is not None, (
        "expected `ci.yml` to scaffold both the FastAPI and Go sample services "
        "before trying to build their Docker images"
    )

    after_fastapi = "\n".join(scripts[fastapi_generate_idx:])
    after_go = "\n".join(scripts[go_generate_idx:])

    builds_fastapi_image = re.search(r"\bdocker build\b.*orders-api", after_fastapi) or (
        re.search(r"\bdocker build\b", after_fastapi) and "orders-api" in after_fastapi
    )
    builds_go_image = re.search(r"\bdocker build\b.*inventory-svc", after_go) or (
        re.search(r"\bdocker build\b", after_go) and "inventory-svc" in after_go
    )

    assert builds_fastapi_image, (
        "ci.yml scaffolds the FastAPI service but never runs `docker build` "
        "against its generated Dockerfile -- a change that breaks the image "
        "build would pass CI undetected"
    )
    assert builds_go_image, (
        "ci.yml scaffolds the Go service but never runs `docker build` "
        "against its generated Dockerfile -- a change that breaks the image "
        "build would pass CI undetected"
    )


def test_ci_applies_k8s_manifests_and_waits_for_pods_ready():
    """CI must apply the generated manifests to a real cluster and wait for Ready pods."""
    ci_text = _ci_text()
    scripts = _all_run_scripts(ci_text)
    combined = "\n".join(scripts)

    creates_cluster = re.search(r"\bkind create cluster\b|\bminikube start\b", combined)
    applies_manifests = re.search(r"\bkubectl apply\b.*k8s", combined) or (
        re.search(r"\bkubectl apply\b", combined) and "k8s" in combined
    )
    waits_for_ready = re.search(
        r"\bkubectl wait\b.*(?:ready|available)|\bkubectl rollout status\b", combined
    )

    assert creates_cluster, (
        "ci.yml never spins up a real Kubernetes cluster (e.g. `kind create "
        "cluster`), so the generated k8s manifests have never actually been "
        "applied anywhere"
    )
    assert applies_manifests, (
        "ci.yml never runs `kubectl apply` against the generated `k8s/` "
        "manifests, so a change that breaks them (e.g. invalid YAML, a bad "
        "probe path) would pass CI undetected"
    )
    assert waits_for_ready, (
        "ci.yml applies the manifests but never waits for the resulting pods "
        "to become Ready, so a crashing container or misconfigured probe "
        "would pass CI undetected"
    )


def test_docs_capture_the_docker_and_kubectl_verification_commands():
    """The issue asks to 'capture the commands in the docs' once verified."""
    readme = (REPO_ROOT / "README.md").read_text()
    golden_path_doc = (REPO_ROOT / "docs" / "golden-path.md").read_text()
    combined_docs = readme + "\n" + golden_path_doc

    has_docker_build_cmd = re.search(r"docker build .*orders-api|docker build .*inventory-svc", combined_docs)
    has_kubectl_apply_cmd = "kubectl apply" in combined_docs
    has_ready_check = re.search(r"kubectl (wait|get pods|rollout status)", combined_docs)

    assert has_docker_build_cmd, (
        "no doc shows the actual `docker build` command used to verify a "
        "generated service's image builds"
    )
    assert has_kubectl_apply_cmd and has_ready_check, (
        "no doc shows the actual `kubectl apply`/readiness-check commands used "
        "to verify a generated service's manifests apply and its pods become Ready"
    )
