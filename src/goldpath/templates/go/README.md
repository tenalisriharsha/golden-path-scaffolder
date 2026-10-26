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
{% if with_k8s %}
## Deploy to Kubernetes

```bash
kubectl apply -f k8s/
```

`k8s/deployment.yaml` and `k8s/service.yaml` wire liveness and readiness
probes to `{{ health_path }}` and set conservative CPU/memory requests and
limits. The deployment uses `imagePullPolicy: IfNotPresent` so a locally
built `{{ service_name }}:latest` image is not re-pulled from a registry.
On local clusters (minikube, kind, Docker Desktop), load the image into the
cluster first so it is present before applying the manifests, e.g.
`minikube image load {{ service_name }}:latest` or
`kind load docker-image {{ service_name }}:latest`.

## Observability

Import `grafana/dashboard.json` into Grafana for a starter dashboard
tracking request rate and total requests via the
`{{ service_slug }}_requests_total` metric.
{% endif %}
## CI

`.github/workflows/ci.yml` vets, tests, builds, and builds the Docker image
on every push and pull request.
