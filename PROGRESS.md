# PROGRESS — golden-path-scaffolder

STATUS: IN_PROGRESS

## Vision

A golden path service scaffolder, the kind platform teams build for internal
developer platforms: one command generates a production-ready service skeleton
with a Dockerfile, GitHub Actions CI, Kubernetes manifests, a Prometheus
metrics endpoint, a Grafana dashboard JSON, and a test setup — so every new
service starts on the "golden path" instead of from a blank directory.

The tool ships with two flavors — **Go** and **FastAPI** — rendered through a
small built-in template engine, and includes docs explaining the golden path
philosophy behind the choices.

## Architecture

```
golden-path-scaffolder/
├── pyproject.toml              # packaging (setuptools, src layout), pytest config
├── src/goldpath/
│   ├── cli.py                  # argparse CLI: `list` and `new` subcommands
│   ├── engine.py               # minimal template engine: {{ var }} + {% if %}/{% endif %}
│   ├── flavors.py              # flavor registry: metadata for go / fastapi
│   ├── scaffold.py             # generation pipeline: walk templates, render, write
│   └── templates/
│       ├── fastapi/            # FastAPI flavor template tree
│       └── go/                 # Go flavor template tree
└── tests/                      # pytest suite mirroring src layout
```

Design decisions:

- **Zero runtime dependencies.** The template engine is a small in-house
  renderer (variable substitution + conditionals, strict on undefined
  variables). No Jinja2, no cookiecutter — the engine itself is part of the
  portfolio.
- **Templates live on disk**, one directory tree per flavor. The pipeline
  walks the tree, renders every file through the engine, and writes it to the
  target directory. Adding a file to a flavor = dropping it in the tree.
- **CLI returns exit codes** (`main(argv) -> int`) so it is fully testable
  without subprocesses.

## Build plan

- [x] **Phase 1 — Core foundation** (Night 1)
  - [x] Project scaffold: pyproject, src layout, venv, .gitignore
  - [x] Template engine (`{{ var }}`, `{% if %}`, strict undefined handling)
  - [x] Flavor registry (`go`, `fastapi`) with validation
  - [x] Generation pipeline + minimal per-flavor skeletons (app entrypoint
        with `/healthz`, README, dependency manifest)
  - [x] CLI: `goldpath list`, `goldpath new <name> --flavor <f>`
  - [x] Full pytest suite, all green
- [x] **Phase 2 — FastAPI flavor, production set** (Night 2)
  - [x] Dockerfile (multi-stage, non-root), requirements pinned
  - [x] GitHub Actions CI workflow (lint, test, build)
  - [x] pytest setup inside the generated service
  - [x] Prometheus metrics endpoint (prometheus-client)
- [x] **Phase 3 — Go flavor, production set** (Night 3)
  - [x] Dockerfile (distroless, multi-stage), go.mod
  - [x] GitHub Actions CI workflow (vet, test, build)
  - [x] Go test setup inside the generated service
  - [x] Prometheus metrics endpoint (promhttp)
- [x] **Phase 4 — Platform assets** (Night 4)
  - [x] Kubernetes manifests (deployment, service, probes, resources)
  - [x] Grafana dashboard JSON per flavor
  - [x] Template conditionals exercised by real flavor options
- [ ] **Phase 5 — Docs & polish** (Night 5)
  - [ ] Golden path philosophy doc (docs/golden-path.md)
  - [ ] README quickstart with real generated output
  - [ ] Final test pass, example generation, release prep

## Resume here (Night 5)

Phase 4 is complete and tested (45 tests, all passing, up from 38). Both
flavors now generate a `k8s/` and `grafana/` subtree in addition to the
existing production set:

- `k8s/deployment.yaml` — 2 replicas, container port from `{{ port }}`,
  `livenessProbe`/`readinessProbe` both `httpGet` against `{{ health_path }}`
  on the named `http` container port, and conservative
  `resources.requests`/`limits` (100m/128Mi requests, 500m/256Mi limits).
- `k8s/service.yaml` — ClusterIP-style Service selecting `app: {{
  service_name }}`, forwarding port `{{ port }}` to the `http` container
  port.
- `grafana/dashboard.json` — a minimal but valid Grafana dashboard (schema
  v39) with two panels (request-rate timeseries, total-requests stat) both
  querying `{{ service_slug }}_requests_total`, the same counter the
  service's own `/metrics` endpoint exposes.

These three files are byte-identical across the `fastapi` and `go` template
trees — the golden path convention (image tag, probe wiring, metric name)
is language-agnostic by design, so there was no reason for the manifests
themselves to differ per flavor.

**This is the phase that put the engine's `{% if %}` conditional to real
use.** Added a `with_k8s: bool` context variable (`build_context(...,
with_k8s=True)`, defaulting on) and a matching `--no-k8s` CLI flag.
`scaffold_service` now skips the `k8s/` and `grafana/` subtrees entirely
when `with_k8s` is false (checked via `relative.parts[0] in _K8S_DIRS`
before rendering — the flag controls which files get written, not just
their content). Both flavor `README.md` templates gained a `{% if
with_k8s %}...{% endif %}` block ("Deploy to Kubernetes" / "Observability"
sections) that only renders when the flag is on — so the conditional is
exercised both at the file-tree level (scaffold.py) and inside a rendered
template (engine.py), covering the two ways a real flavor option could
need to behave.

Verified for real: rendered a service into `/tmp`, confirmed
`grafana/dashboard.json` round-trips through `json.loads` (valid JSON,
not just no leftover `{{`), and confirmed `k8s/deployment.yaml` /
`service.yaml` parse cleanly with `yaml.safe_load` (PyYAML installed
into `.venv` for this check only, not a project dependency) and report
the correct `kind`. `kubectl apply --dry-run=client` was not usable in
this environment — no live cluster, and this kubectl build insists on
API-server discovery even with `--validate=false` — so live schema
validation against the Kubernetes API is the one thing still unverified,
same caveat class as Phase 3's untested Docker build.

New tests in `tests/test_scaffold.py`: a parametrized
`test_scaffold_platform_assets` (both flavors) checking file presence,
rendered probe/resource content, valid JSON dashboard, and the README's
conditional section; `test_scaffold_without_k8s_skips_platform_assets`
checking the flag actually removes `k8s/`/`grafana/` from the written-file
list and the README section; `test_build_context_with_k8s_flag_defaults_true`.
Also two new CLI tests for `--no-k8s`. Existing production-set tests'
`len(written)` assertions bumped (fastapi 10→13, go 8→11) to account for
the three new files per flavor.

Tomorrow night — Phase 5 (final phase):

1. Write `docs/golden-path.md`: the philosophy doc explaining *why* each
   piece of the generated service exists (why probes wired to a real health
   check, why a non-root/distroless runtime image, why a request counter by
   default, why k8s manifests ship even though `--no-k8s` exists). This is
   pure writing, no code changes — pull the "why" from the design notes
   already scattered across this file's phase entries.
2. README quickstart: consider replacing the hand-maintained tree diagrams
   with real output of `goldpath new` run against a temp dir, so the
   README can't drift from what the tool actually generates.
3. Final test pass across both the tool's own suite and a fresh generated
   service of each flavor (Python: pytest + ruff; Go: go vet + go test +
   go build) — same manual verification pattern used in Phases 2 and 3.
4. Write `DAILY_REPORT.md` summarizing all 5 nights: what got built, final
   test counts, known limitations (no live Docker/kubectl verification in
   this environment, template engine intentionally has no expression
   language), and future ideas (more flavors, `--with-*` options beyond
   k8s, a real end-to-end smoke test that builds+runs the Docker image).
5. Only then flip `STATUS` to `COMPLETE` in this file.
