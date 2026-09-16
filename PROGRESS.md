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
- [ ] **Phase 3 — Go flavor, production set** (Night 3)
  - [ ] Dockerfile (distroless, multi-stage), go.mod
  - [ ] GitHub Actions CI workflow (vet, test, build)
  - [ ] Go test setup inside the generated service
  - [ ] Prometheus metrics endpoint (promhttp)
- [ ] **Phase 4 — Platform assets** (Night 4)
  - [ ] Kubernetes manifests (deployment, service, probes, resources)
  - [ ] Grafana dashboard JSON per flavor
  - [ ] Template conditionals exercised by real flavor options
- [ ] **Phase 5 — Docs & polish** (Night 5)
  - [ ] Golden path philosophy doc (docs/golden-path.md)
  - [ ] README quickstart with real generated output
  - [ ] Final test pass, example generation, release prep

## Resume here (Night 3)

Phase 2 is complete and tested (37 tests, all passing). The FastAPI flavor
now generates the full production set:

- `Dockerfile` (multi-stage, non-root `appuser`, `EXPOSE {{ port }}`)
- `.dockerignore`
- `.github/workflows/ci.yml` (install deps, `ruff check`, `pytest`,
  `docker build`)
- `requirements-dev.txt` (pytest, httpx, ruff) alongside the runtime
  `requirements.txt` (now also pins `prometheus-client`)
- `conftest.py` at the generated service root so `tests/` can `import app`
- `app/main.py` gained a request-counting middleware
  (`Counter("<service_slug>_requests_total", ...)`) and a `GET /metrics`
  endpoint returning Prometheus exposition format
- `tests/test_health.py` exercising both `/healthz` and `/metrics`

New context variable: `service_slug` (`build_context` in `scaffold.py`) —
the service name with hyphens replaced by underscores, since Prometheus
metric names can't contain hyphens. Verified manually: generated a service
into `/tmp`, installed its requirements, ran its own `pytest` and
`ruff check` inside a fresh venv — both green.

Packaging gotcha found and fixed: setuptools' `package-data` glob
(`templates/**/*`) silently drops dotfiles and dot-directories (`.dockerignore`,
`.github/workflows/ci.yml`) — Python's `glob` module never matches hidden
entries via `*`, even recursively. Confirmed by building a wheel and
inspecting it; the new files were missing. Fixed by adding `MANIFEST.in`
(`recursive-include src/goldpath/templates *`) plus
`include-package-data = true` in `pyproject.toml`, then re-verified the
built wheel contains all 10 fastapi template files. Any future flavor with
dotfiles (the Go flavor will need `.github/workflows/`) is covered by the
same fix — no per-flavor changes needed.

Tomorrow night:

1. Start Phase 3: bring the Go flavor (`src/goldpath/templates/go/`) up to
   the same production set — Dockerfile (distroless, multi-stage),
   `.github/workflows/ci.yml` (vet, test, build), a Go test file
   (`cmd/server/main_test.go` or similar) and a Prometheus metrics endpoint
   via `promhttp`.
2. Decide how to expose a metric-safe identifier for Go (mirror
   `service_slug`, though Go metric names use underscores too so the same
   context variable should work as-is).
3. Add tests in `tests/test_scaffold.py` mirroring the FastAPI production-set
   test added tonight (`test_scaffold_fastapi_production_set`).
4. Keep the zero-dependency rule for the *scaffolder*; dependencies like
   `prometheus-client` or `promhttp` belong to the *generated* service only.
