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
- [ ] **Phase 4 — Platform assets** (Night 4)
  - [ ] Kubernetes manifests (deployment, service, probes, resources)
  - [ ] Grafana dashboard JSON per flavor
  - [ ] Template conditionals exercised by real flavor options
- [ ] **Phase 5 — Docs & polish** (Night 5)
  - [ ] Golden path philosophy doc (docs/golden-path.md)
  - [ ] README quickstart with real generated output
  - [ ] Final test pass, example generation, release prep

## Resume here (Night 4)

Phase 3 is complete and tested (38 tests, all passing). The Go flavor now
generates the full production set, mirroring FastAPI's:

- `Dockerfile` (multi-stage: `golang:1.25` builder → `gcr.io/distroless/
  static-debian12` runtime, `CGO_ENABLED=0`, `EXPOSE {{ port }}`)
- `.dockerignore`
- `.github/workflows/ci.yml` (`go vet`, `go test`, `go build`,
  `docker build`)
- `go.mod` + `go.sum` pinning `github.com/prometheus/client_golang v1.24.1`
  and its transitive deps — a real, verified dependency graph, not a stub
- `cmd/server/main.go` gained a `countRequests` middleware (wraps
  `http.Handler`, records status via a `statusRecorder`) feeding a
  `promauto.NewCounterVec("<service_slug>_requests_total", ...)` labeled by
  path/method/status_code, and a `GET /metrics` endpoint via
  `promhttp.Handler()`
- `cmd/server/main_test.go` exercising both `/healthz` and `/metrics` with
  `httptest`

No new context variables needed — `service_slug` (added in Phase 2) already
covers Go's underscore-only metric name requirement.

Verified for real, not just by inspection: installed Go 1.27.1 via
`brew install go` (network was available in this environment). Generated a
service into `/tmp`, then ran `go vet ./...`, `go test ./... -v` (both
`TestHealth` and `TestMetrics` pass), and `go build` — all using only the
vendored `go.sum`, no `go mod tidy` needed at generation time. Also ran the
built binary directly and curled `/healthz` and `/metrics` to confirm the
counter increments and exposition format is correct. Rebuilt the wheel and
confirmed all 8 Go template files — including the two dotfile paths
(`.dockerignore`, `.github/workflows/ci.yml`) — are present, so the Phase 2
packaging fix (`MANIFEST.in`) covers this flavor with no changes.

Design note: went with a hand-written `countRequests` middleware instead of
reaching for a routing library, since `net/http`'s `http.ServeMux` (Go
1.22+, method+path patterns) is enough — keeps the generated service's own
dependency footprint to exactly one third-party module
(`prometheus/client_golang`), same spirit as FastAPI pulling in only
`prometheus-client`.

Docker build itself was not verified (no local Docker daemon in this
environment) — only `go build` of the binary. If Docker becomes available,
worth a one-time check that the distroless image actually runs the binary.

Tomorrow night:

1. Start Phase 4: Kubernetes manifests (`deployment.yaml`, `service.yaml`,
   liveness/readiness probes wired to `{{ health_path }}`, resource
   requests/limits) and a Grafana dashboard JSON per flavor, both driven off
   the existing context variables (`service_name`, `service_slug`, `port`,
   `health_path`).
2. This is the first phase that will actually exercise the engine's
   `{% if %}` conditionals for real (e.g. an optional `--with-k8s` or
   flavor-specific dashboard panel differences) — so far every template has
   been unconditional. Check whether `scaffold_service`/`build_context`
   need a new boolean context flag, or whether flavor differences alone are
   enough.
3. Add tests in `tests/test_scaffold.py` for the k8s/Grafana file set per
   flavor, following the same "assert file exists, assert rendered content,
   assert no leftover `{{`" pattern as the two production-set tests.
4. Keep manifests generic/portable — no cloud-specific annotations unless
   flagged as an explicit option.
