# golden-path-scaffolder

One command scaffolds a production-ready service on the **golden path** —
the same kind of internal tool platform teams build so that every new
service starts with the right defaults instead of a blank directory.

```bash
goldpath new orders-api --flavor fastapi
```

## Project Status

**In active development** — built in public, one phase per night.
See [PROGRESS.md](PROGRESS.md) for the vision, architecture, phased build
plan, and exactly where the build resumes next.

## What a generated service gets

| Asset | Status |
| --- | --- |
| Service skeleton with `/healthz` endpoint (Go or FastAPI) | ✅ Phase 1 |
| Template engine (`{{ var }}`, `{% if %}`), zero dependencies | ✅ Phase 1 |
| Dockerfile + GitHub Actions CI (FastAPI) | ✅ Phase 2 |
| Test setup inside the generated service (FastAPI) | ✅ Phase 2 |
| Prometheus metrics endpoint (FastAPI) | ✅ Phase 2 |
| Dockerfile + GitHub Actions CI (Go) | Phase 3 |
| Test setup + Prometheus metrics (Go) | Phase 3 |
| Kubernetes manifests + Grafana dashboard JSON | Phase 4 |
| Golden path philosophy docs | Phase 5 |

## Usage

```bash
pip install -e .
goldpath list                          # show available flavors
goldpath new orders-api --flavor fastapi --output ./services
```

A generated FastAPI service now includes the full production set:

```
orders-api/
├── Dockerfile               # multi-stage build, non-root user
├── .dockerignore
├── .github/workflows/ci.yml # lint, test, build on push/PR
├── README.md
├── requirements.txt         # fastapi, uvicorn, prometheus-client
├── requirements-dev.txt     # pytest, httpx, ruff
├── conftest.py
├── app/
│   ├── __init__.py
│   └── main.py              # /healthz + /metrics (Prometheus) endpoints
└── tests/
    └── test_health.py
```

Every request the generated service handles is counted in a
`<service>_requests_total` Prometheus counter, exposed on `GET /metrics`.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest
pytest
```

The scaffolder itself has **zero runtime dependencies** — the template
engine is built in-house. Dependencies like `fastapi` or `uvicorn` belong
to the *generated* services, not to this tool.

## Layout

- `src/goldpath/engine.py` — template engine
- `src/goldpath/flavors.py` — flavor registry (`go`, `fastapi`)
- `src/goldpath/scaffold.py` — generation pipeline
- `src/goldpath/cli.py` — `goldpath` CLI
- `src/goldpath/templates/` — one template tree per flavor
- `tests/` — pytest suite
