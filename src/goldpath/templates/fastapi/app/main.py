"""{{ service_name }} — FastAPI entrypoint."""

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

app = FastAPI(title="{{ service_name }}")

REQUEST_COUNT = Counter(
    "{{ service_slug }}_requests_total",
    "Total HTTP requests handled by {{ service_name }}.",
    ["path", "method", "status_code"],
)


@app.middleware("http")
async def count_requests(request: Request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
    ).inc()
    return response


@app.get("{{ health_path }}")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "{{ service_name }}"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
