"""{{ service_name }} — FastAPI entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="{{ service_name }}")


@app.get("{{ health_path }}")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "{{ service_name }}"}
