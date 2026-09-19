# DAILY_REPORT — golden-path-scaffolder

Five-night build of a golden-path service scaffolder: a CLI that generates a
production-ready service skeleton (Go or FastAPI) with a Dockerfile, CI
workflow, test setup, Prometheus metrics, Kubernetes manifests, and a
Grafana dashboard — all rendered through a small in-house template engine.

## Night by night

**Night 1 — Core foundation.** Project scaffold (`pyproject.toml`, src
layout), the template engine (`{{ var }}` substitution and `{% if %}`
conditionals, strict on undefined variables and unbalanced tags), the
flavor registry (`go`, `fastapi`), the generation pipeline
(`scaffold_service`), and the `goldpath list` / `goldpath new` CLI. Each
flavor's initial skeleton was an app entrypoint with `/healthz`, a README,
and a dependency manifest. Established the pattern used for the rest of the
project: `main(argv) -> int` so the CLI is testable without subprocesses.

**Night 2 — FastAPI production set.** Multi-stage, non-root Dockerfile;
GitHub Actions CI (lint, test, build); a pytest setup inside the generated
service; a Prometheus `/metrics` endpoint backed by a
`<service>_requests_total` counter wired into FastAPI middleware. Also
fixed a packaging bug (`db94355`) where dotfiles (`.dockerignore`,
`.github/`) weren't being included in the packaged template trees.

**Night 3 — Go production set.** The same production set, in Go: a
multi-stage Dockerfile with a distroless runtime image, a GitHub Actions CI
workflow (vet, test, build), a `go test` setup, and the equivalent
Prometheus counter via `promhttp`. This established that the "production
set" is a platform convention, not a FastAPI-specific one.

**Night 4 — Platform assets.** Kubernetes manifests (`k8s/deployment.yaml`,
`k8s/service.yaml`) and a Grafana dashboard (`grafana/dashboard.json`),
identical across both flavors since deployment convention doesn't depend on
language. This is the phase that put the engine's `{% if %}` conditional to
real use: a `with_k8s` context flag (default on, `--no-k8s` to skip) that
both omits whole subtrees from the written-file list in `scaffold.py` and
gates a rendered section in each flavor's own `README.md` template.

**Night 5 — Docs & polish (this session).** Wrote `docs/golden-path.md`,
explaining the reasoning behind every default: why the health check is real
instead of a stub, why probes are wired to that same path, why the runtime
images are non-root/distroless, why a request counter ships unconditioned
on the developer adding one, why Kubernetes manifests are on by default
with an opt-out, why the template engine deliberately has no expression
language, and why the platform assets are byte-identical across flavors.
Verified the README's hand-written tree diagrams against real
`goldpath new` output (still accurate, no drift). Ran a full manual
verification pass: generated a fresh service of each flavor into a temp
directory and exercised it for real —

- FastAPI: installed `requirements.txt` + `requirements-dev.txt` into a
  fresh venv, ran `pytest` (2 passed) and `ruff check .` (clean).
- Go: `go vet ./...`, `go build ./...`, `go test ./...` — all clean.
- Both: `grafana/dashboard.json` round-trips through `json.loads`.

Updated README.md's status table and added a link to the new docs.

## Final state

- 45 tests in the tool's own suite, all passing (`pytest -q` from the repo
  root).
- Both generated flavors verified end-to-end as above.
- Zero runtime dependencies in the scaffolder itself — only the generated
  services carry dependencies (`fastapi`/`uvicorn`/`prometheus-client` for
  Python, `client_golang` for Go), and those are pinned in the templates.

## Known limitations

- **No live Docker build or `kubectl apply` verification.** Neither Docker
  nor a Kubernetes cluster was available in this environment across any of
  the five nights. The Dockerfiles were reviewed by hand for correctness
  (multi-stage, non-root/distroless, correct `EXPOSE`/`CMD`), and the k8s
  manifests were validated with `yaml.safe_load` for well-formedness and
  correct `kind`, but neither was validated against the real Docker daemon
  or the Kubernetes API schema.
- **Template engine has no expression language by design** (see
  `docs/golden-path.md`) — this is a considered tradeoff, not a gap, but it
  does mean any future flavor option more complex than a boolean toggle
  will need to be modeled as a new boolean (or several) rather than as an
  expression inside a template.
- **Two flavors only.** The k8s/Grafana convention being flavor-agnostic
  makes adding a third flavor mostly a matter of writing its app-specific
  templates, but that's still untested beyond the two that exist.
- **No end-to-end smoke test that actually builds and runs the generated
  Docker image** inside the tool's own test suite — the closest thing is
  the manual verification pass described above, which isn't automated or
  repeatable in CI.

## Future ideas

- A real end-to-end smoke test (in an environment with Docker available)
  that builds the generated image, runs it, and curls `/healthz` and
  `/metrics` — the strongest possible guarantee that a generated service
  actually works, not just that its files parse.
- More flavors (Node/Express, Rust/axum) to further validate that the
  platform-asset convention genuinely is language-agnostic.
- `--with-*` options beyond `--no-k8s` — e.g. an opt-in OpenTelemetry
  tracing setup, or a choice of base image — using the same context-flag
  pattern `with_k8s` established.
- `kubectl apply --dry-run=server` (or a tool like `kubeconform`) against
  the generated manifests once a cluster or an offline schema validator is
  available, to close the one verification gap noted above.
