# {{ service_name }}

A {{ language }} service scaffolded with [golden-path-scaffolder](https://github.com/tenalisriharsha/golden-path-scaffolder).

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --port {{ port }}
```

Health check: `GET {{ health_path }}`
Metrics: `GET /metrics` (Prometheus exposition format)

## Run with Docker

```bash
docker build -t {{ service_name }} .
docker run --rm -p {{ port }}:{{ port }} {{ service_name }}
```

The image builds in two stages and runs as a non-root user.

## Test

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
ruff check .
```

## CI

`.github/workflows/ci.yml` installs dependencies, lints with ruff, runs the
test suite, and builds the Docker image on every push and pull request.
