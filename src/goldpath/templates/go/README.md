# {{ service_name }}

A {{ language }} service scaffolded with [golden-path-scaffolder](https://github.com/tenalisriharsha/golden-path-scaffolder).

## Run locally

```bash
go run ./cmd/server
```

Health check: `GET {{ health_path }}`
Metrics: `GET /metrics` (Prometheus exposition format)

## Run with Docker

```bash
docker build -t {{ service_name }} .
docker run --rm -p {{ port }}:{{ port }} {{ service_name }}
```

The image builds in two stages and runs distroless (no shell, no package
manager, just the static binary).

## Test

```bash
go vet ./...
go test ./...
```

## CI

`.github/workflows/ci.yml` vets, tests, builds, and builds the Docker image
on every push and pull request.
