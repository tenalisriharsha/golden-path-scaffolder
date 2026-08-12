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
- [ ] **Phase 2 — FastAPI flavor, production set** (Night 2)
  - [ ] Dockerfile (multi-stage, non-root), requirements pinned
  - [ ] GitHub Actions CI workflow (lint, test, build)
  - [ ] pytest setup inside the generated service
  - [ ] Prometheus metrics endpoint (prometheus-client)
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

## Resume here (Night 2)

Phase 1 is complete and tested (35 tests, all passing). Tomorrow night:

1. Start Phase 2: expand `src/goldpath/templates/fastapi/` with the full
   production set — Dockerfile, `.github/workflows/ci.yml`, tests dir,
   Prometheus metrics in `app/main.py`.
2. Add tests in `tests/test_scaffold.py` asserting the new files render and
   contain the expected content (health endpoint, metrics route, image name).
3. Keep the zero-dependency rule for the *scaffolder*; dependencies like
   `prometheus-client` belong to the *generated* service only.
